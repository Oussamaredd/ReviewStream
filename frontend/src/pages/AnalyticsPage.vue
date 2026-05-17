<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

import BarChart from "../components/BarChart.vue";
import EmptyState from "../components/EmptyState.vue";
import LoadingState from "../components/LoadingState.vue";
import MetricCard from "../components/MetricCard.vue";
import ProductTable from "../components/ProductTable.vue";
import RecentReviews from "../components/RecentReviews.vue";
import ScoreDistribution from "../components/ScoreDistribution.vue";
import StatusBanner from "../components/StatusBanner.vue";
import { getDashboard } from "../services/api";

const pollIntervalMs = 10000;
const dashboardStorageKey = "reviewstream.dashboard.v2";
const legacyDashboardStorageKey = "reviewstream.dashboard.v1";

const dashboard = ref(null);
const isLoading = ref(false);
const warningMessage = ref("");
const errorMessage = ref("");
const lastUpdated = ref("");
let pollTimer = null;

const summary = computed(() => {
  return (
    dashboard.value?.summary || {
      total_reviews: 0,
      average_score: 0,
      first_review_at: null,
      last_review_at: null,
    }
  );
});

const sentiment = computed(() => dashboard.value?.sentiment || []);
const scoreDistribution = computed(() => dashboard.value?.score_distribution || []);
const topProducts = computed(() => filterTestProducts(dashboard.value?.top_products || []));
const worstProducts = computed(() => filterTestProducts(dashboard.value?.worst_products || []));
const negativeProducts = computed(() =>
  filterTestProducts(dashboard.value?.negative_products || [])
);
const sources = computed(() => dashboard.value?.sources || []);
const recentReviews = computed(() => filterOpinionRows(dashboard.value?.recent_reviews || []));
const opinions = computed(() => {
  return filterOpinionRows(dashboard.value?.opinions || recentReviews.value || []);
});
const positiveKeywordCount = computed(() => {
  return dashboard.value?.positive_keywords?.matching_reviews ?? 0;
});
const negativeKeywordCount = computed(() => {
  return dashboard.value?.negative_keywords?.matching_reviews ?? 0;
});

const statusLabel = computed(() => {
  if (!dashboard.value) {
    return "Waiting for analytics";
  }

  if (dashboard.value.status === "sample") {
    return "Sample analytics";
  }

  if (dashboard.value.status === "cached" || dashboard.value.stale) {
    return "Cached snapshot";
  }

  return "Fresh from Hive";
});

const metricCards = computed(() => [
  {
    label: "Total reviews",
    value: formatInteger(summary.value.total_reviews),
    detail: "Hive silver rows",
    featured: true,
  },
  {
    label: "Average score",
    value: formatDecimal(summary.value.average_score),
    detail: "All scored reviews",
    featured: true,
  },
  {
    label: "First review",
    value: formatDate(summary.value.first_review_at),
    detail: "Oldest event",
  },
  {
    label: "Latest review",
    value: formatDate(summary.value.last_review_at),
    detail: "Newest event",
  },
  {
    label: "Positive keywords",
    value: formatInteger(positiveKeywordCount.value),
    detail: "Opinion text hits",
  },
  {
    label: "Negative keywords",
    value: formatInteger(negativeKeywordCount.value),
    detail: "Opinion text hits",
  },
]);

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

function isTestProduct(row) {
  return String(row?.product_id || "")
    .toUpperCase()
    .startsWith("E2E");
}

function hasOpinionText(row) {
  return Boolean(String(row?.text || "").trim());
}

function filterTestProducts(rows) {
  return rows.filter((row) => !isTestProduct(row));
}

function filterOpinionRows(rows) {
  return rows.filter((row) => !isTestProduct(row) && hasOpinionText(row));
}

function dashboardWarning(data) {
  if (data.status === "sample") {
    return "Showing sample analytics while Hive warms up. Seed data or fix Hive to replace this with live analytics.";
  }

  if (data.status === "cached" || data.stale) {
    return "Showing cached analytics. Hive is currently unavailable.";
  }

  return "";
}

function restoreDashboardFromStorage() {
  try {
    window.localStorage.removeItem(legacyDashboardStorageKey);
    const cachedDashboard = JSON.parse(window.localStorage.getItem(dashboardStorageKey));
    if (!cachedDashboard?.summary) {
      return;
    }

    dashboard.value = {
      ...cachedDashboard,
      status: "cached",
      stale: true,
      warning: "Loaded from browser cache while analytics refresh.",
    };
    warningMessage.value = "Showing cached analytics from this browser while analytics refresh.";
    lastUpdated.value = new Date().toLocaleTimeString();
  } catch {
    window.localStorage.removeItem(dashboardStorageKey);
  }
}

function persistDashboard(data) {
  if (!data?.summary || data.status === "sample") {
    return;
  }

  window.localStorage.setItem(dashboardStorageKey, JSON.stringify(data));
}

async function loadDashboard({ silent = false } = {}) {
  if (isLoading.value) {
    return;
  }

  isLoading.value = !silent;

  try {
    const data = await getDashboard({
      preferCache: true,
      allowSample: true,
      timeoutMs: 2500,
    });
    dashboard.value = data;
    persistDashboard(data);
    errorMessage.value = "";
    lastUpdated.value = new Date().toLocaleTimeString();
    warningMessage.value = dashboardWarning(data);
  } catch (error) {
    if (dashboard.value) {
      warningMessage.value = "Analytics refresh failed. Showing the previous dashboard snapshot.";
      errorMessage.value = "";
      return;
    }

    if (error?.status === 503) {
      errorMessage.value =
        "Analytics are not ready yet. Start Hive, initialize the table, or seed sample data.";
    } else {
      errorMessage.value =
        error instanceof Error ? error.message : "Analytics could not be loaded.";
    }
  } finally {
    isLoading.value = false;
  }
}

onMounted(() => {
  restoreDashboardFromStorage();
  loadDashboard({ silent: Boolean(dashboard.value) });
  pollTimer = window.setInterval(() => loadDashboard({ silent: true }), pollIntervalMs);
});

onBeforeUnmount(() => {
  if (pollTimer) {
    window.clearInterval(pollTimer);
  }
});
</script>

<template>
  <main class="page-shell analytics-page">
    <section class="page-heading compact analytics-heading">
      <div>
        <p class="eyebrow">Analytics</p>
        <h1>Review operations</h1>
        <p>Product performance, sentiment, and opinion signals from the analytics pipeline.</p>
      </div>
      <div class="analytics-command-bar">
        <span :class="['dashboard-status', dashboard?.status || 'pending']">
          {{ statusLabel }}
        </span>
        <div class="analytics-refresh-line">
          <span v-if="lastUpdated">Refreshed {{ lastUpdated }}</span>
          <span>Polling {{ pollIntervalMs / 1000 }}s</span>
        </div>
      </div>
    </section>

    <div v-if="warningMessage || errorMessage" class="analytics-alerts">
      <StatusBanner v-if="warningMessage" type="warning" :message="warningMessage" />
      <StatusBanner v-if="errorMessage" type="error" :message="errorMessage" />
    </div>

    <LoadingState v-if="isLoading && !dashboard" label="Loading analytics" />

    <template v-else-if="dashboard">
      <section class="metrics-grid" aria-label="Summary metrics">
        <MetricCard
          v-for="metric in metricCards"
          :key="metric.label"
          :class="{ featured: metric.featured }"
          :label="metric.label"
          :value="metric.value"
          :detail="metric.detail"
        />
      </section>

      <section class="analytics-section">
        <div class="section-heading">
          <div>
            <p class="panel-kicker">Customer voice</p>
            <h2>Opinion feed</h2>
          </div>
          <span>Read the latest review text before interpreting aggregate ratios</span>
        </div>

        <div class="analytics-grid text-insights">
          <RecentReviews
            title="Opinion text"
            kicker="Review content"
            :rows="opinions"
            empty-message="No opinions yet"
          />
          <RecentReviews
            title="Recent reviews"
            kicker="Latest opinions"
            :rows="recentReviews"
            empty-message="No recent review text yet"
          />
        </div>
      </section>

      <section class="analytics-section">
        <div class="section-heading">
          <div>
            <p class="panel-kicker">Distribution</p>
            <h2>Ratio views</h2>
          </div>
          <span>Use these after scanning the underlying opinions</span>
        </div>

        <div class="analytics-grid analytics-overview-grid">
          <BarChart
            title="Sentiment distribution"
            kicker="Opinion tone"
            :rows="sentiment"
            label-key="sentiment"
            empty-message="No sentiment rows yet"
          />
          <ScoreDistribution :rows="scoreDistribution" />
          <BarChart
            title="Source counts"
            kicker="Data mix"
            :rows="sources"
            label-key="source"
            empty-message="No source rows yet"
          />
        </div>
      </section>

      <section class="analytics-section">
        <div class="section-heading">
          <div>
            <p class="panel-kicker">Product performance</p>
            <h2>Ranked product signals</h2>
          </div>
          <span>Review volume, average score, and negative-review concentration</span>
        </div>

        <div class="analytics-grid product-insights">
          <ProductTable
            title="Top products"
            kicker="Best rated"
            :rows="topProducts"
            empty-message="No top products yet"
          />
          <ProductTable
            title="Worst products"
            kicker="Lowest rated"
            :rows="worstProducts"
            empty-message="No worst products yet"
          />
          <ProductTable
            title="Negative products"
            kicker="Risk signals"
            :rows="negativeProducts"
            count-label="Negative"
            count-key="negative_review_count"
            empty-message="No negative product rows yet"
          />
        </div>
      </section>
    </template>

    <EmptyState
      v-else-if="!isLoading"
      title="Analytics unavailable"
      message="Start Hive, initialize the table, or seed sample data."
    />
  </main>
</template>
