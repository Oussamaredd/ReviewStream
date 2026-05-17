<script setup>
import { computed, reactive } from "vue";

const props = defineProps({
  product: {
    type: Object,
    required: true,
  },
  submitting: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["submit", "cancel"]);

const scoreOptions = [1, 2, 3, 4, 5];
const form = reactive({
  score: 5,
  text: "",
});

const textLength = computed(() => form.text.length);
const scoreLabel = computed(() => `${form.score} ${form.score === 1 ? "star" : "stars"}`);
const canSubmit = computed(() => {
  return form.text.trim() && textLength.value <= 2000 && !props.submitting;
});

function formatPrice(value) {
  const number = Number(value ?? 0);
  return Number.isFinite(number)
    ? number.toLocaleString([], { style: "currency", currency: "USD" })
    : "$0.00";
}

function submitReview() {
  if (!canSubmit.value) {
    return;
  }

  emit("submit", {
    score: Number(form.score),
    text: form.text.trim(),
  });
}
</script>

<template>
  <form class="review-form" @submit.prevent="submitReview">
    <div class="selected-product">
      <img :src="product.image_url" :alt="product.name" />
      <div>
        <span>{{ product.category }}</span>
        <strong>{{ product.name }}</strong>
        <small>{{ formatPrice(product.price) }}</small>
      </div>
    </div>

    <div class="field">
      <span>Score</span>
      <div class="star-rating" role="radiogroup" aria-label="Review score">
        <button
          v-for="score in scoreOptions"
          :key="score"
          type="button"
          :class="['star-button', { active: score <= form.score }]"
          :aria-label="`${score} ${score === 1 ? 'star' : 'stars'}`"
          :aria-pressed="form.score === score"
          @click="form.score = score"
        >
          <span aria-hidden="true">★</span>
        </button>
        <strong>{{ scoreLabel }}</strong>
      </div>
    </div>

    <label class="field">
      <span class="field-row">
        <span>Opinion</span>
        <small>{{ textLength }}/2000</small>
      </span>
      <textarea
        v-model="form.text"
        maxlength="2000"
        rows="7"
        placeholder="Fresh flavor, quick delivery, and easy to recommend."
      ></textarea>
    </label>

    <div class="form-actions">
      <button type="button" class="secondary-button" @click="$emit('cancel')">Cancel</button>
      <button type="submit" class="primary-button" :disabled="!canSubmit">
        {{ submitting ? "Queueing..." : "Submit review" }}
      </button>
    </div>
  </form>
</template>
