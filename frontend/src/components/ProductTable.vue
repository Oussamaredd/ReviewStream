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
  countLabel: {
    type: String,
    default: "Reviews",
  },
  countKey: {
    type: String,
    default: "review_count",
  },
  emptyMessage: {
    type: String,
    default: "No products yet",
  },
});

function formatInteger(value) {
  const number = Number(value ?? 0);
  return Number.isFinite(number) ? number.toLocaleString() : "0";
}

function formatDecimal(value) {
  const number = Number(value ?? 0);
  return Number.isFinite(number) ? number.toFixed(2) : "0.00";
}

function productLabel(row) {
  return row.product_name || row.product_id || "Unknown product";
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

    <table v-if="rows.length" class="data-table">
      <thead>
        <tr>
          <th>Product</th>
          <th>{{ countLabel }}</th>
          <th>Avg</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="`${row.product_id}-${countKey}`">
          <td>
            <strong>{{ productLabel(row) }}</strong>
            <span v-if="row.product_id" class="table-subtext">{{ row.product_id }}</span>
          </td>
          <td>{{ formatInteger(row[countKey]) }}</td>
          <td>{{ formatDecimal(row.average_score) }}</td>
        </tr>
      </tbody>
    </table>

    <div v-else class="compact-empty">{{ emptyMessage }}</div>
  </section>
</template>
