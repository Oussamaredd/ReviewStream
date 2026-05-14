<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";

const pollIntervalMs = 5000;

const scoreOptions = [1, 2, 3, 4, 5];

const form = reactive({
  product_id: "",
  user_id: "",
  score: 5,
  text: "",
  source: "web",
});

const dashboard = ref(null);
const health = ref({ status: "checking", label: "Checking API" });
const isDashboardLoading = ref(false);
const dashboardError = ref("");
const lastUpdated = ref("");
const isSubmitting = ref(false);
const submitError = ref("");
const submission = ref(null);
let pollTimer = null;

const textLength = computed(() => form.text.length);
const canSubmit = computed(() => {
  return (
    form.product_id.trim() &&
    form.user_id.trim() &&
    form.text.trim() &&
    textLength.value <= 2000 &&
    !isSubmitting.value
  );
});

const summary = computed(() => dashboard.value?.summary ?? {});
const sentiment = computed(() => dashboard.value?.sentiment ?? []);
const scoreDistribution = computed(() => dashboard.value?.score_distribution ?? []);
const topProducts = computed(() => dashboard.value?.top_products ?? []);
const worstProducts = computed(() => dashboard.value?.worst_products ?? []);
const negativeProducts = computed(() => dashboard.value?.negative_products ?? []);
const recentReviews = computed(() => dashboard.value?.recent_reviews ?? []);
const sources = computed(() => dashboard.value?.sources ?? []);

const maxSentimentCount = computed(() => maxCount(sentiment.value));
const maxScoreCount = computed(() => maxCount(scoreDistribution.value));

const metricCards = computed(() => [
  {
    label: "Total reviews",
    value: formatInteger(summary.value.total_reviews),
    detail: "Historical and live rows",
  },
  {
    label: "Average score",
    value: formatDecimal(summary.value.average_score),
    detail: "Across Hive silver data",
  },
  {
    label: "First review",
    value: formatDate(summary.value.first_review_at),
    detail: "Oldest event in analytics",
  },
  {
    label: "Latest review",
    value: formatDate(summary.value.last_review_at),
    detail: "Newest event in analytics",
  },
]);

function maxCount(rows) {
  return rows.reduce((current, row) => Math.max(current, Number(row.review_count ?? 0)), 0);
}

function formatInteger(value) {
  const number = Number(value ?? 0);
  return Number.isFinite(number) ? number.toLocaleString() : "0";
}

function formatDecimal(value) {
  const number = Number(value ?? 0);
  return Number.isFinite(number) ? number.toFixed(2) : "0.00";
}

function formatDate(value) {
  if (!value) {
    return "No data";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function scoreCount(score) {
  const row = scoreDistribution.value.find((item) => Number(item.score) === score);
  return Number(row?.review_count ?? 0);
}

function percent(count, max) {
  if (!max) {
    return "0%";
  }

  return `${Math.max(6, Math.round((Number(count) / max) * 100))}%`;
}

async function checkHealth() {
  try {
    const response = await fetch("/api/health");
    if (!response.ok) {
      throw new Error("Health request failed");
    }

    const data = await response.json();
    health.value = {
      status: "online",
      label: `API online on Kafka topic ${data.kafka_topic}`,
    };
  } catch {
    health.value = {
      status: "offline",
      label: "API offline",
    };
  }
}

async function loadDashboard() {
  if (isDashboardLoading.value) {
    return;
  }

  isDashboardLoading.value = true;
  dashboardError.value = "";

  try {
    const response = await fetch("/api/analytics/dashboard");
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Dashboard analytics request failed");
    }

    dashboard.value = data;
    lastUpdated.value = new Date().toLocaleTimeString();
  } catch (error) {
    dashboardError.value = error instanceof Error ? error.message : "Unexpected analytics error";
  } finally {
    isDashboardLoading.value = false;
  }
}

async function submitReview() {
  if (!canSubmit.value) {
    return;
  }

  isSubmitting.value = true;
  submitError.value = "";
  submission.value = null;

  try {
    const response = await fetch("/api/reviews", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        product_id: form.product_id.trim(),
        user_id: form.user_id.trim(),
        score: Number(form.score),
        text: form.text.trim(),
        source: form.source.trim() || "web",
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Review submission failed");
    }

    submission.value = data;
    form.product_id = "";
    form.user_id = "";
    form.score = 5;
    form.text = "";
    await loadDashboard();
  } catch (error) {
    submitError.value = error instanceof Error ? error.message : "Unexpected submission error";
  } finally {
    isSubmitting.value = false;
  }
}

onMounted(() => {
  checkHealth();
  loadDashboard();
  pollTimer = window.setInterval(loadDashboard, pollIntervalMs);
});

onBeforeUnmount(() => {
  if (pollTimer) {
    window.clearInterval(pollTimer);
  }
});
</script>

<template>
  <main class="app-shell">
    <header class="topbar">
      <div>
        <p class="eyebrow">ReviewStream</p>
        <h1>Ecommerce Review Analytics</h1>
      </div>
      <div class="status-stack">
        <span :class="['status-pill', health.status]">{{ health.label }}</span>
        <span class="refresh-note">
          Polls every {{ pollIntervalMs / 1000 }}s
          <template v-if="lastUpdated"> - Updated {{ lastUpdated }}</template>
        </span>
      </div>
    </header>

    <section class="notice">
      Reviews are queued immediately after submission. Kafka, Spark, HDFS, and Hive make analytics
      eventually consistent, so dashboard totals may update a few seconds later.
    </section>

    <section class="metrics-grid" aria-label="Summary metrics">
      <article v-for="metric in metricCards" :key="metric.label" class="metric-card">
        <span>{{ metric.label }}</span>
        <strong>{{ metric.value }}</strong>
        <small>{{ metric.detail }}</small>
      </article>
    </section>

    <section class="workspace">
      <form class="panel review-form" @submit.prevent="submitReview">
        <div class="panel-header">
          <div>
            <p class="panel-kicker">Live input</p>
            <h2>Submit review</h2>
          </div>
          <span class="source-badge">{{ form.source }}</span>
        </div>

        <label class="field">
          <span>Product ID</span>
          <input v-model="form.product_id" type="text" maxlength="100" placeholder="P001" />
        </label>

        <label class="field">
          <span>User ID</span>
          <input v-model="form.user_id" type="text" maxlength="100" placeholder="client1" />
        </label>

        <label class="field">
          <span>Source</span>
          <input v-model="form.source" type="text" maxlength="50" placeholder="web" />
        </label>

        <div class="field">
          <span>Score</span>
          <div class="score-control">
            <button
              v-for="score in scoreOptions"
              :key="score"
              type="button"
              :class="['score-button', { active: form.score === score }]"
              @click="form.score = score"
            >
              {{ score }}
            </button>
          </div>
        </div>

        <label class="field">
          <span class="field-row">
            <span>Review text</span>
            <small>{{ textLength }}/2000</small>
          </span>
          <textarea
            v-model="form.text"
            maxlength="2000"
            rows="6"
            placeholder="Fresh, tasty, and easy to recommend."
          ></textarea>
        </label>

        <div v-if="submitError" class="message error">{{ submitError }}</div>
        <div v-if="submission" class="message success">
          Queued review {{ submission.review.review_id }} at Kafka offset
          {{ submission.kafka.offset }}. Analytics will catch up after Spark writes silver data.
        </div>

        <button class="primary-button" type="submit" :disabled="!canSubmit">
          {{ isSubmitting ? "Sending..." : "Send review" }}
        </button>
      </form>

      <section class="panel">
        <div class="panel-header">
          <div>
            <p class="panel-kicker">Distribution</p>
            <h2>Sentiment and scores</h2>
          </div>
          <span v-if="isDashboardLoading" class="small-muted">Refreshing</span>
        </div>

        <div v-if="dashboardError" class="message error">{{ dashboardError }}</div>

        <div class="bar-list">
          <div v-for="row in sentiment" :key="row.sentiment" class="bar-row">
            <span class="bar-label">{{ row.sentiment }}</span>
            <div class="bar-track">
              <span
                class="bar-fill sentiment"
                :style="{ width: percent(row.review_count, maxSentimentCount) }"
              ></span>
            </div>
            <strong>{{ formatInteger(row.review_count) }}</strong>
          </div>
        </div>

        <div class="score-bars">
          <div v-for="score in scoreOptions" :key="score" class="score-bar">
            <span>{{ score }}</span>
            <div class="vertical-track">
              <span
                class="vertical-fill"
                :style="{ height: percent(scoreCount(score), maxScoreCount) }"
              ></span>
            </div>
            <strong>{{ formatInteger(scoreCount(score)) }}</strong>
          </div>
        </div>
      </section>
    </section>

    <section class="analytics-grid">
      <section class="panel">
        <div class="panel-header">
          <div>
            <p class="panel-kicker">Best rated</p>
            <h2>Top products</h2>
          </div>
        </div>
        <table>
          <thead>
            <tr>
              <th>Product</th>
              <th>Reviews</th>
              <th>Avg</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in topProducts" :key="row.product_id">
              <td>{{ row.product_id }}</td>
              <td>{{ formatInteger(row.review_count) }}</td>
              <td>{{ formatDecimal(row.average_score) }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section class="panel">
        <div class="panel-header">
          <div>
            <p class="panel-kicker">Lowest rated</p>
            <h2>Worst products</h2>
          </div>
        </div>
        <table>
          <thead>
            <tr>
              <th>Product</th>
              <th>Reviews</th>
              <th>Avg</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in worstProducts" :key="row.product_id">
              <td>{{ row.product_id }}</td>
              <td>{{ formatInteger(row.review_count) }}</td>
              <td>{{ formatDecimal(row.average_score) }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section class="panel">
        <div class="panel-header">
          <div>
            <p class="panel-kicker">Risk signals</p>
            <h2>Negative products</h2>
          </div>
        </div>
        <table>
          <thead>
            <tr>
              <th>Product</th>
              <th>Negative</th>
              <th>Avg</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in negativeProducts" :key="row.product_id">
              <td>{{ row.product_id }}</td>
              <td>{{ formatInteger(row.negative_review_count) }}</td>
              <td>{{ formatDecimal(row.average_score) }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section class="panel">
        <div class="panel-header">
          <div>
            <p class="panel-kicker">Sources</p>
            <h2>Data mix</h2>
          </div>
        </div>
        <div class="source-list">
          <div v-for="row in sources" :key="row.source" class="source-row">
            <span>{{ row.source }}</span>
            <strong>{{ formatInteger(row.review_count) }}</strong>
          </div>
        </div>
      </section>
    </section>

    <section class="panel">
      <div class="panel-header">
        <div>
          <p class="panel-kicker">Latest silver rows</p>
          <h2>Recent reviews</h2>
        </div>
      </div>

      <div class="recent-list">
        <article v-for="row in recentReviews" :key="row.review_id" class="recent-item">
          <div>
            <strong>{{ row.product_id }}</strong>
            <span>{{ row.source }} - {{ row.sentiment }} - score {{ row.score }}</span>
          </div>
          <p v-if="row.text">{{ row.text }}</p>
          <small>
            {{ formatDate(row.created_at) }} - {{ formatInteger(row.word_count) }} words
            <span v-if="row.has_positive_keywords"> - positive keyword</span>
            <span v-if="row.has_negative_keywords"> - negative keyword</span>
          </small>
        </article>
      </div>
    </section>
  </main>
</template>

<style scoped>
:global(*) {
  box-sizing: border-box;
}

:global(body) {
  margin: 0;
  background: #f4f6f8;
  color: #1f2933;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI",
    sans-serif;
}

:global(button),
:global(input),
:global(textarea) {
  font: inherit;
}

.app-shell {
  width: min(1440px, 100%);
  margin: 0 auto;
  padding: 24px;
}

.topbar {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: flex-start;
  padding: 8px 0 20px;
}

.eyebrow,
.panel-kicker {
  margin: 0 0 6px;
  color: #4f46e5;
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

h1,
h2 {
  margin: 0;
  letter-spacing: 0;
}

h1 {
  font-size: clamp(2rem, 4vw, 3.5rem);
  line-height: 1;
}

h2 {
  font-size: 1.15rem;
}

.status-stack {
  display: grid;
  justify-items: end;
  gap: 6px;
}

.status-pill,
.source-badge {
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 0.85rem;
  font-weight: 700;
}

.status-pill.online {
  background: #dff8ea;
  color: #146c43;
}

.status-pill.offline {
  background: #fde8e8;
  color: #b42318;
}

.status-pill.checking,
.source-badge {
  background: #e8edff;
  color: #3730a3;
}

.refresh-note,
.small-muted,
small {
  color: #6b7280;
  font-size: 0.82rem;
}

.notice,
.panel,
.metric-card {
  border: 1px solid #d9dee7;
  border-radius: 8px;
  background: #ffffff;
}

.notice {
  margin-bottom: 16px;
  padding: 12px 14px;
  color: #425466;
  line-height: 1.5;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.metric-card {
  display: grid;
  gap: 6px;
  padding: 16px;
}

.metric-card span,
.field span,
th {
  color: #52606d;
  font-size: 0.82rem;
  font-weight: 700;
}

.metric-card strong {
  font-size: clamp(1.4rem, 3vw, 2.2rem);
  line-height: 1;
}

.workspace {
  display: grid;
  grid-template-columns: minmax(320px, 0.9fr) minmax(420px, 1.1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.analytics-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.panel {
  padding: 16px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 16px;
}

.review-form,
.field {
  display: grid;
  gap: 10px;
}

.review-form {
  align-content: start;
}

.field-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

input,
textarea {
  width: 100%;
  border: 1px solid #c9d2df;
  border-radius: 6px;
  background: #ffffff;
  color: #1f2933;
  padding: 10px 12px;
}

textarea {
  resize: vertical;
  min-height: 132px;
}

input:focus,
textarea:focus {
  border-color: #4f46e5;
  outline: 3px solid #e8edff;
}

.score-control {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 8px;
}

.score-button {
  min-height: 40px;
  border: 1px solid #c9d2df;
  border-radius: 6px;
  background: #f8fafc;
  color: #1f2933;
  cursor: pointer;
  font-weight: 800;
}

.score-button.active {
  border-color: #4f46e5;
  background: #eef2ff;
  color: #3730a3;
}

.primary-button {
  width: 100%;
  min-height: 44px;
  border: 0;
  border-radius: 6px;
  background: #146c43;
  color: #ffffff;
  cursor: pointer;
  font-weight: 800;
}

.primary-button:disabled {
  background: #9aa6b2;
  cursor: not-allowed;
}

.message {
  border-radius: 6px;
  padding: 10px 12px;
  line-height: 1.45;
}

.message.error {
  background: #fde8e8;
  color: #9b1c1c;
}

.message.success {
  background: #dff8ea;
  color: #146c43;
}

.bar-list {
  display: grid;
  gap: 10px;
  margin-bottom: 24px;
}

.bar-row {
  display: grid;
  grid-template-columns: 92px 1fr 64px;
  gap: 10px;
  align-items: center;
}

.bar-label {
  text-transform: capitalize;
}

.bar-track,
.vertical-track {
  overflow: hidden;
  border-radius: 999px;
  background: #edf1f7;
}

.bar-track {
  height: 12px;
}

.bar-fill {
  display: block;
  height: 100%;
  border-radius: inherit;
}

.bar-fill.sentiment {
  background: #0e7490;
}

.score-bars {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
  min-height: 180px;
}

.score-bar {
  display: grid;
  grid-template-rows: auto 1fr auto;
  gap: 8px;
  justify-items: center;
}

.vertical-track {
  display: flex;
  align-items: flex-end;
  width: 100%;
  min-height: 120px;
}

.vertical-fill {
  display: block;
  width: 100%;
  border-radius: inherit;
  background: #f59e0b;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th,
td {
  padding: 10px 8px;
  border-bottom: 1px solid #edf1f7;
  text-align: left;
  vertical-align: top;
}

td:last-child,
th:last-child {
  text-align: right;
}

.source-list,
.recent-list {
  display: grid;
  gap: 10px;
}

.source-row {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 0;
  border-bottom: 1px solid #edf1f7;
}

.recent-item {
  display: grid;
  gap: 8px;
  border: 1px solid #edf1f7;
  border-radius: 8px;
  padding: 12px;
}

.recent-item div {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.recent-item p {
  margin: 0;
  color: #3e4c59;
  line-height: 1.45;
}

@media (max-width: 1180px) {
  .analytics-grid,
  .metrics-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .workspace {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .app-shell {
    padding: 14px;
  }

  .topbar,
  .recent-item div {
    display: grid;
  }

  .status-stack {
    justify-items: start;
  }

  .analytics-grid,
  .metrics-grid {
    grid-template-columns: 1fr;
  }

  .bar-row {
    grid-template-columns: 76px 1fr 48px;
  }
}
</style>
