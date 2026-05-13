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
	$(VENV)/bin/black backend

lint:
	$(VENV)/bin/ruff check backend

check:
	$(PY) -m compileall backend
	$(VENV)/bin/ruff check backend
	$(VENV)/bin/black --check backend

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
