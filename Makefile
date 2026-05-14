SHELL := /bin/bash

PYTHON := python3
VENV := .venv
PIP := $(VENV)/bin/pip
PY := $(VENV)/bin/python
UVICORN := $(VENV)/bin/uvicorn

.PHONY: help setup install dev-install docker-up docker-down docker-logs kafka-topic api health test-review consume smoke format lint check doctor clean

help:
	@echo "ReviewStream commands:"
	@echo "  make setup         Create venv and install dependencies"
	@echo "  make install       Install Python dependencies"
	@echo "  make dev-install   Install development dependencies"
	@echo "  make docker-up     Start Kafka, Zookeeper, and Kafka UI"
	@echo "  make docker-down   Stop Docker services"
	@echo "  make docker-logs   Show Docker logs"
	@echo "  make kafka-topic   Create Kafka topic: reviews"
	@echo "  make api           Run FastAPI backend"
	@echo "  make health        Test API health endpoint"
	@echo "  make test-review   Send a sample review to the API"
	@echo "  make consume       Read messages from Kafka"
	@echo "  make smoke         Run health + review send + Kafka consume"
	@echo "  make format        Format backend code"
	@echo "  make lint          Lint backend code"
	@echo "  make check         Compile + lint + formatting check"
	@echo "  make doctor        Show local tool versions"
	@echo "  make clean         Remove Python cache files"

setup:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

install:
	$(PIP) install -r requirements.txt

dev-install:
	$(PIP) install -r requirements-dev.txt

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

kafka-topic:
	docker exec reviewstream-kafka kafka-topics \
		--bootstrap-server localhost:29092 \
		--create \
		--if-not-exists \
		--topic reviews \
		--partitions 1 \
		--replication-factor 1

api:
	$(UVICORN) backend.app.main:app --reload --port 8000

health:
	curl http://localhost:8000/health

test-review:
	curl -X POST http://localhost:8000/reviews \
		-H "Content-Type: application/json" \
		-d '{"product_id":"P001","user_id":"client1","score":5,"text":"Great product from Makefile!"}'

consume:
	docker exec reviewstream-kafka kafka-console-consumer \
		--bootstrap-server localhost:29092 \
		--topic reviews \
		--from-beginning \
		--max-messages 5

smoke:
	$(MAKE) health
	$(MAKE) test-review
	$(MAKE) consume

format:
	$(VENV)/bin/black backend spark

lint:
	$(VENV)/bin/ruff check backend spark

check:
	$(PY) -m compileall backend spark
	$(VENV)/bin/ruff check backend spark
	$(VENV)/bin/black --check backend spark

doctor:
	@echo "Python:"
	@$(PY) --version
	@echo "Pip:"
	@$(PIP) --version
	@echo "Docker:"
	@docker --version
	@echo "Docker Compose:"
	@docker compose version
	@echo "Git branch:"
	@git branch --show-current

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

SPARK_SUBMIT := $(VENV)/bin/spark-submit
SPARK_KAFKA_PACKAGE := org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.1

.PHONY: spark-stream spark-version

spark-version:
	PATH="$(PWD)/$(VENV)/bin:$$PATH" $(SPARK_SUBMIT) --version

spark-stream:
	PATH="$(PWD)/$(VENV)/bin:$$PATH" \
	PYSPARK_PYTHON="$(PWD)/$(PY)" \
	PYSPARK_DRIVER_PYTHON="$(PWD)/$(PY)" \
	$(SPARK_SUBMIT) \
		--packages $(SPARK_KAFKA_PACKAGE) \
		spark/streaming_reviews.py

.PHONY: spark-analytics

spark-analytics:
	PATH="$(PWD)/$(VENV)/bin:$$PATH" \
	PYSPARK_PYTHON="$(PWD)/$(PY)" \
	PYSPARK_DRIVER_PYTHON="$(PWD)/$(PY)" \
	$(SPARK_SUBMIT) \
		--packages $(SPARK_KAFKA_PACKAGE) \
		spark/streaming_analytics.py

.PHONY: hdfs-init hdfs-ls hdfs-cat-bronze spark-storage

hdfs-init:
	docker exec reviewstream-namenode hdfs dfs -mkdir -p /reviewstream/bronze/reviews_raw
	docker exec reviewstream-namenode hdfs dfs -mkdir -p /reviewstream/silver/reviews_enriched
	docker exec reviewstream-namenode hdfs dfs -mkdir -p /reviewstream/checkpoints
	docker exec reviewstream-namenode hdfs dfs -chmod -R 777 /reviewstream

hdfs-ls:
	docker exec reviewstream-namenode hdfs dfs -ls -R /reviewstream

hdfs-cat-bronze:
	docker exec reviewstream-datanode hdfs dfs -cat "/reviewstream/bronze/reviews_raw/*.json" | head -n 10

spark-storage:
	PATH="$(PWD)/$(VENV)/bin:$$PATH" \
	PYSPARK_PYTHON="$(PWD)/$(PY)" \
	PYSPARK_DRIVER_PYTHON="$(PWD)/$(PY)" \
	$(SPARK_SUBMIT) \
		--packages $(SPARK_KAFKA_PACKAGE) \
		spark/streaming_to_hdfs.py

.PHONY: hdfs-wait

hdfs-wait:
	@echo "Waiting for HDFS NameNode..."
	@until docker exec reviewstream-namenode hdfs dfsadmin -report >/dev/null 2>&1; do \
		echo "HDFS not ready yet..."; \
		sleep 5; \
	done
	@echo "HDFS is ready."

.PHONY: spark-read-silver

spark-read-silver:
	PATH="$(PWD)/$(VENV)/bin:$$PATH" \
	PYSPARK_PYTHON="$(PWD)/$(PY)" \
	PYSPARK_DRIVER_PYTHON="$(PWD)/$(PY)" \
	$(SPARK_SUBMIT) spark/read_silver_reviews.py

.PHONY: hive-wait hive-init hive-shell hive-query

hive-wait:
	@echo "Waiting for HiveServer2..."
	@until docker exec reviewstream-hive-server beeline -u 'jdbc:hive2://localhost:10000/reviewstream;auth=noSasl' -n root -e "SELECT 1;" >/dev/null 2>&1; do \
		echo "Hive not ready yet..."; \
		sleep 5; \
	done
	@echo "Hive is ready."

hive-init:
	docker cp hive/init.sql reviewstream-hive-server:/tmp/reviewstream_hive_init.sql
	docker exec reviewstream-hive-server beeline -u 'jdbc:hive2://localhost:10000/reviewstream;auth=noSasl' -n root -f /tmp/reviewstream_hive_init.sql

hive-shell:
	docker exec -it reviewstream-hive-server beeline -u 'jdbc:hive2://localhost:10000/reviewstream;auth=noSasl' -n root

hive-query:
	docker exec reviewstream-hive-server beeline -u 'jdbc:hive2://localhost:10000/reviewstream;auth=noSasl' -n root -e "USE reviewstream; SELECT sentiment, COUNT(*) AS review_count FROM reviews_enriched GROUP BY sentiment; SELECT product_id, COUNT(*) AS review_count, AVG(score) AS average_score FROM reviews_enriched GROUP BY product_id;"

.PHONY: hive-metastore-init hive-tables

hive-metastore-init:
	docker compose stop hive-server hive-metastore || true
	docker compose run --rm hive-metastore bash -lc '/opt/hive/bin/schematool -dbType postgres -info || /opt/hive/bin/schematool -dbType postgres -initSchema --verbose'
	docker compose up -d hive-metastore hive-server
	$(MAKE) hive-wait

hive-tables:
	docker exec reviewstream-hive-server beeline -u 'jdbc:hive2://localhost:10000/reviewstream;auth=noSasl' -n root -e "SHOW TABLES; DESCRIBE reviews_enriched; SELECT COUNT(*) AS total_reviews FROM reviews_enriched; SELECT * FROM reviews_enriched LIMIT 10;"