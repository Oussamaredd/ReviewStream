<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from "vue";

import EmptyState from "../components/EmptyState.vue";
import LoadingState from "../components/LoadingState.vue";
import ProductCard from "../components/ProductCard.vue";
import ReviewForm from "../components/ReviewForm.vue";
import StatusBanner from "../components/StatusBanner.vue";
import { getProducts, submitProductReview } from "../services/api";

const products = ref([]);
const selectedProduct = ref(null);
const isLoading = ref(true);
const isSubmitting = ref(false);
const loadError = ref("");
const submitError = ref("");
const successMessage = ref("");
const searchTerm = ref("");
const selectedCategory = ref("All");
const formResetKey = ref(0);
const reviewDialog = ref(null);

const categories = computed(() => {
  const values = new Set(products.value.map((product) => product.category));
  return ["All", ...Array.from(values).sort()];
});

const filteredProducts = computed(() => {
  const search = searchTerm.value.trim().toLowerCase();

  return products.value.filter((product) => {
    const matchesCategory =
      selectedCategory.value === "All" || product.category === selectedCategory.value;
    const searchable = [
      product.name,
      product.category,
      product.description,
      ...(product.tags || []),
    ]
      .join(" ")
      .toLowerCase();

    return matchesCategory && (!search || searchable.includes(search));
  });
});

async function loadProducts() {
  isLoading.value = true;
  loadError.value = "";

  try {
    products.value = await getProducts();
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : "Products could not be loaded.";
  } finally {
    isLoading.value = false;
  }
}

function chooseProduct(product) {
  selectedProduct.value = product;
  submitError.value = "";
  successMessage.value = "";
  nextTick(() => reviewDialog.value?.focus());
}

function closeReviewPanel() {
  if (isSubmitting.value) {
    return;
  }

  selectedProduct.value = null;
  submitError.value = "";
}

function handleKeydown(event) {
  if (event.key === "Escape" && selectedProduct.value) {
    closeReviewPanel();
  }
}

async function submitReview(payload) {
  if (!selectedProduct.value) {
    return;
  }

  isSubmitting.value = true;
  submitError.value = "";
  successMessage.value = "";

  try {
    await submitProductReview(selectedProduct.value.product_id, payload);
    successMessage.value = "Review queued. Analytics will update after Spark and Hive catch up.";
    formResetKey.value += 1;
  } catch (error) {
    submitError.value =
      error instanceof Error ? error.message : "Review could not be queued. Try again.";
  } finally {
    isSubmitting.value = false;
  }
}

onMounted(() => {
  loadProducts();
  window.addEventListener("keydown", handleKeydown);
});

onUnmounted(() => {
  window.removeEventListener("keydown", handleKeydown);
});
</script>

<template>
  <main class="page-shell products-page">
    <section class="page-heading">
      <div>
        <p class="eyebrow">Product reviews</p>
        <h1>Shop the demo catalog</h1>
        <p>
          Choose a product, add a score and opinion, and ReviewStream will queue the review for
          the live analytics pipeline.
        </p>
      </div>
      <StatusBanner
        type="info"
        message="Reviews are queued immediately. Analytics are eventually consistent after Spark writes to HDFS and Hive reads the silver table."
      />
    </section>

    <LoadingState v-if="isLoading" label="Loading products" />
    <StatusBanner v-else-if="loadError" type="error" :message="loadError" />

    <template v-else>
      <section class="catalog-toolbar" aria-label="Product filters">
        <label class="search-field">
          <span>Search</span>
          <input v-model="searchTerm" type="search" placeholder="Tea, coffee, snacks" />
        </label>

        <div class="segmented-control" aria-label="Category filter">
          <button
            v-for="category in categories"
            :key="category"
            type="button"
            :class="{ active: selectedCategory === category }"
            @click="selectedCategory = category"
          >
            {{ category }}
          </button>
        </div>
      </section>

      <section class="product-grid" aria-label="Products">
        <ProductCard
          v-for="product in filteredProducts"
          :key="product.product_id"
          :product="product"
          :selected="selectedProduct?.product_id === product.product_id"
          @review="chooseProduct"
        />

        <EmptyState
          v-if="!filteredProducts.length"
          title="No products match"
          message="Adjust the search or category filter."
        />
      </section>

      <Teleport to="body">
        <div
          v-if="selectedProduct"
          class="review-modal-backdrop"
          @click.self="closeReviewPanel"
        >
          <aside
            ref="reviewDialog"
            class="review-panel review-dialog-panel"
            role="dialog"
            aria-modal="true"
            aria-labelledby="review-dialog-title"
            tabindex="-1"
          >
            <div class="panel-header">
              <div>
                <p class="panel-kicker">Checkout counter</p>
                <h2 id="review-dialog-title">Leave a review</h2>
              </div>
              <button type="button" class="secondary-button" @click="closeReviewPanel">
                Close
              </button>
            </div>

            <ReviewForm
              :key="`${selectedProduct.product_id}-${formResetKey}`"
              :product="selectedProduct"
              :submitting="isSubmitting"
              @submit="submitReview"
              @cancel="closeReviewPanel"
            />

            <StatusBanner v-if="successMessage" type="success" :message="successMessage" />
            <StatusBanner v-if="submitError" type="error" :message="submitError" />
          </aside>
        </div>
      </Teleport>
    </template>
  </main>
</template>
