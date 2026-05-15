<script setup>
defineProps({
  title: {
    type: String,
    required: true,
  },
  kicker: {
    type: String,
    default: "",
  },
  rows: {
    type: Array,
    default: () => [],
  },
  emptyMessage: {
    type: String,
    default: "No review text yet",
  },
});

function formatInteger(value) {
  const number = Number(value ?? 0);
  return Number.isFinite(number) ? number.toLocaleString() : "0";
}

function formatDate(value) {
  if (!value) {
    return "No date";
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

function productLabel(row) {
  return row.product_name || row.product_id || "Unknown product";
}
</script>

<template>
  <section class="panel review-text-panel">
    <div class="panel-header">
      <div>
        <p v-if="kicker" class="panel-kicker">{{ kicker }}</p>
        <h2>{{ title }}</h2>
      </div>
    </div>

    <div v-if="rows.length" class="review-list">
      <article v-for="row in rows" :key="row.review_id" class="review-item">
        <header>
          <div>
            <strong>{{ productLabel(row) }}</strong>
            <span>{{ row.source || "unknown" }} · {{ row.sentiment || "unknown" }}</span>
          </div>
          <span class="score-pill">Score {{ row.score }}</span>
        </header>
        <p>{{ row.text || "No opinion text available." }}</p>
        <footer>
          <span>{{ formatDate(row.created_at) }}</span>
          <span>{{ formatInteger(row.word_count) }} words</span>
          <span v-if="row.has_positive_keywords">positive keyword</span>
          <span v-if="row.has_negative_keywords">negative keyword</span>
        </footer>
      </article>
    </div>

    <div v-else class="compact-empty">{{ emptyMessage }}</div>
  </section>
</template>
