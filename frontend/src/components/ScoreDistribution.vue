<script setup>
import { computed } from "vue";

const props = defineProps({
  rows: {
    type: Array,
    default: () => [],
  },
});

const scores = [1, 2, 3, 4, 5];

const maxCount = computed(() => {
  return scores.reduce((current, score) => Math.max(current, scoreCount(score)), 0);
});

function scoreCount(score) {
  const row = props.rows.find((item) => Number(item.score) === score);
  return Number(row?.review_count ?? 0);
}

function formatInteger(value) {
  const number = Number(value ?? 0);
  return Number.isFinite(number) ? number.toLocaleString() : "0";
}

function heightFor(value) {
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
        <p class="panel-kicker">Ratings</p>
        <h2>Score distribution</h2>
      </div>
    </div>

    <div class="score-bars">
      <div v-for="score in scores" :key="score" class="score-bar">
        <span>{{ score }}</span>
        <div class="vertical-track">
          <span class="vertical-fill" :style="{ height: heightFor(scoreCount(score)) }"></span>
        </div>
        <strong>{{ formatInteger(scoreCount(score)) }}</strong>
      </div>
    </div>
  </section>
</template>
