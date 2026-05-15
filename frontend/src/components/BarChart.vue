<script setup>
import { computed } from "vue";

const props = defineProps({
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
  labelKey: {
    type: String,
    required: true,
  },
  countKey: {
    type: String,
    default: "review_count",
  },
  emptyMessage: {
    type: String,
    default: "No rows yet",
  },
});

const maxCount = computed(() => {
  return props.rows.reduce((current, row) => {
    return Math.max(current, Number(row[props.countKey] ?? 0));
  }, 0);
});

function formatInteger(value) {
  const number = Number(value ?? 0);
  return Number.isFinite(number) ? number.toLocaleString() : "0";
}

function widthFor(value) {
  if (!maxCount.value) {
    return "0%";
  }

  return `${Math.max(6, Math.round((Number(value) / maxCount.value) * 100))}%`;
}
</script>

<template>
  <section class="panel">
    <div class="panel-header">
      <div>
        <p v-if="kicker" class="panel-kicker">{{ kicker }}</p>
        <h2>{{ title }}</h2>
      </div>
    </div>

    <div v-if="rows.length" class="bar-list">
      <div v-for="row in rows" :key="row[labelKey]" class="bar-row">
        <span class="bar-label">{{ row[labelKey] }}</span>
        <div class="bar-track">
          <span class="bar-fill" :style="{ width: widthFor(row[countKey]) }"></span>
        </div>
        <strong>{{ formatInteger(row[countKey]) }}</strong>
      </div>
    </div>

    <div v-else class="compact-empty">{{ emptyMessage }}</div>
  </section>
</template>
