<script setup>
defineProps({
  title: {
    type: String,
    default: "No data",
  },
  message: {
    type: String,
    default: "",
  },
});
</script>

<template>
  <div class="state-box empty-state">
    <strong>{{ title }}</strong>
    <span v-if="message">{{ message }}</span>
  </div>
</template>
