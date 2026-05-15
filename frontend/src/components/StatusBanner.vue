<script setup>
defineProps({
  type: {
    type: String,
    default: "info",
  },
  title: {
    type: String,
    default: "",
  },
  message: {
    type: String,
    required: true,
  },
});
</script>

<template>
  <div :class="['status-banner', type]" role="status">
    <strong v-if="title">{{ title }}</strong>
    <span>{{ message }}</span>
  </div>
</template>
