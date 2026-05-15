<script setup>
defineProps({
  label: {
    type: String,
    default: "Loading",
  },
});
</script>

<template>
  <div class="state-box loading-state">
    <span class="spinner" aria-hidden="true"></span>
    <span>{{ label }}</span>
  </div>
</template>
