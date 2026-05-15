<script setup>
defineProps({
  product: {
    type: Object,
    required: true,
  },
  selected: {
    type: Boolean,
    default: false,
  },
});

defineEmits(["review"]);

function formatPrice(value) {
  const number = Number(value ?? 0);
  return Number.isFinite(number)
    ? number.toLocaleString([], { style: "currency", currency: "USD" })
    : "$0.00";
}
</script>

<template>
  <article :class="['product-card', { selected }]">
    <img :src="product.image_url" :alt="product.name" loading="lazy" />
    <div class="product-card-body">
      <div class="product-card-top">
        <span class="category-pill">{{ product.category }}</span>
        <strong>{{ formatPrice(product.price) }}</strong>
      </div>
      <h2>{{ product.name }}</h2>
      <p>{{ product.description }}</p>
      <div class="tag-row">
        <span v-for="tag in product.tags" :key="tag">{{ tag }}</span>
      </div>
      <button type="button" class="primary-button" @click="$emit('review', product)">
        Review product
      </button>
    </div>
  </article>
</template>
