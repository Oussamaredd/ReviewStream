<script setup>
import { computed, onMounted, reactive, ref } from "vue";

const scoreOptions = [
  { value: 1, label: "1", tone: "Rough" },
  { value: 2, label: "2", tone: "Weak" },
  { value: 3, label: "3", tone: "Fair" },
  { value: 4, label: "4", tone: "Strong" },
  { value: 5, label: "5", tone: "Excellent" },
];

const form = reactive({
  product_id: "",
  user_id: "",
  score: 5,
  text: "",
  source: "web",
});

const isSubmitting = ref(false);
const submitError = ref("");
const submission = ref(null);
const health = ref({
  status: "checking",
  label: "Checking backend",
});

const textLength = computed(() => form.text.length);
const canSubmit = computed(() => {
  return (
    form.product_id.trim() &&
    form.user_id.trim() &&
    form.text.trim() &&
    textLength.value <= 2000 &&
    !isSubmitting.value
  );
});

async function checkHealth() {
  try {
    const response = await fetch("/api/health");

    if (!response.ok) {
      throw new Error("Health request failed");
    }

    const data = await response.json();
    health.value = {
      status: "online",
      label: `Live on topic ${data.kafka_topic}`,
    };
  } catch {
    health.value = {
      status: "offline",
      label: "Backend unreachable",
    };
  }
}

async function submitReview() {
  if (!canSubmit.value) {
    return;
  }

  isSubmitting.value = true;
  submitError.value = "";

  try {
    const response = await fetch("/api/reviews", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        product_id: form.product_id.trim(),
        user_id: form.user_id.trim(),
        score: form.score,
        text: form.text.trim(),
        source: form.source,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Review submission failed");
    }

    submission.value = data;
    form.product_id = "";
    form.user_id = "";
    form.score = 5;
    form.text = "";
  } catch (error) {
    submitError.value =
      error instanceof Error ? error.message : "Unexpected error";
  } finally {
    isSubmitting.value = false;
  }
}

onMounted(() => {
  checkHealth();
});
</script>

<template>
  <div class="shell">
    <div class="ambient ambient-left"></div>
    <div class="ambient ambient-right"></div>

    <main class="layout">
      <section class="hero">
        <p class="eyebrow">ReviewStream</p>
        <h1>Turn quick reactions into structured product feedback.</h1>
        <p class="lede">
          Capture customer sentiment in one sharp, low-friction form and send it
          straight into the review pipeline.
        </p>

        <div class="hero-cards">
          <article class="signal-card">
            <span class="signal-label">Pipeline status</span>
            <strong :class="['signal-value', health.status]">
              {{ health.label }}
            </strong>
          </article>

          <article class="signal-card">
            <span class="signal-label">Form model</span>
            <strong class="signal-value static">Product + user + rating + text</strong>
          </article>
        </div>
      </section>

      <section class="panel">
        <div class="panel-head">
          <div>
            <p class="panel-kicker">Customer Review Form</p>
            <h2>Leave the product verdict.</h2>
          </div>
          <span class="source-pill">{{ form.source }}</span>
        </div>

        <form class="review-form" @submit.prevent="submitReview">
          <label class="field">
            <span>Product ID</span>
            <input v-model="form.product_id" type="text" maxlength="100" placeholder="P001" />
          </label>

          <label class="field">
            <span>User ID</span>
            <input v-model="form.user_id" type="text" maxlength="100" placeholder="client1" />
          </label>

          <div class="field">
            <span>Score</span>
            <div class="score-grid">
              <button
                v-for="option in scoreOptions"
                :key="option.value"
                type="button"
                :class="['score-chip', { active: form.score === option.value }]"
                @click="form.score = option.value"
              >
                <strong>{{ option.label }}</strong>
                <small>{{ option.tone }}</small>
              </button>
            </div>
          </div>

          <label class="field">
            <div class="field-row">
              <span>Review</span>
              <small :class="{ warning: textLength > 1800 }">{{ textLength }}/2000</small>
            </div>
            <textarea
              v-model="form.text"
              rows="6"
              maxlength="2000"
              placeholder="What stood out, what failed, and what should improve?"
            ></textarea>
          </label>

          <div v-if="submitError" class="message error">
            {{ submitError }}
          </div>

          <div v-if="submission" class="message success">
            <strong>{{ submission.message }}</strong>
            <span>
              Review {{ submission.review.review_id }} queued on partition
              {{ submission.kafka.partition }} at offset
              {{ submission.kafka.offset }}.
            </span>
          </div>

          <div class="actions">
            <button class="submit-button" type="submit" :disabled="!canSubmit">
              {{ isSubmitting ? "Sending..." : "Send Review" }}
            </button>
            <p class="hint">The backend generates the review ID and timestamp.</p>
          </div>
        </form>
      </section>
    </main>
  </div>
</template>

<style scoped>
:global(*) {
  box-sizing: border-box;
}

:global(body) {
  margin: 0;
  background:
    radial-gradient(circle at top left, rgba(255, 178, 102, 0.24), transparent 28%),
    radial-gradient(circle at bottom right, rgba(83, 171, 255, 0.18), transparent 30%),
    linear-gradient(145deg, #f7f1e8 0%, #efe2d2 48%, #ead9cc 100%);
  color: #1b1a18;
  font-family: "Aptos", "Segoe UI Variable Text", "Segoe UI", sans-serif;
}

:global(button),
:global(input),
:global(textarea) {
  font: inherit;
}

.shell {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
}

.ambient {
  position: absolute;
  border-radius: 999px;
  filter: blur(20px);
  opacity: 0.75;
}

.ambient-left {
  top: -4rem;
  left: -4rem;
  width: 16rem;
  height: 16rem;
  background: rgba(255, 146, 77, 0.3);
}

.ambient-right {
  right: -6rem;
  bottom: 4rem;
  width: 20rem;
  height: 20rem;
  background: rgba(34, 113, 255, 0.18);
}

.layout {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: 1.05fr 0.95fr;
  gap: 2rem;
  max-width: 1200px;
  margin: 0 auto;
  padding: 3rem 1.5rem;
}

.hero {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 1rem 0;
}

.eyebrow,
.panel-kicker {
  margin: 0 0 0.75rem;
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #9b4920;
}

.hero h1,
.panel h2 {
  margin: 0;
  font-family: "Georgia", "Times New Roman", serif;
  font-weight: 700;
  line-height: 0.95;
}

.hero h1 {
  max-width: 11ch;
  font-size: clamp(3.25rem, 7vw, 6.25rem);
}

.lede {
  max-width: 34rem;
  margin: 1.5rem 0 0;
  font-size: 1.1rem;
  line-height: 1.7;
  color: rgba(27, 26, 24, 0.75);
}

.hero-cards {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
  margin-top: 2rem;
}

.signal-card,
.panel {
  border: 1px solid rgba(61, 49, 38, 0.1);
  background: rgba(255, 251, 245, 0.8);
  box-shadow: 0 16px 45px rgba(97, 68, 39, 0.08);
  backdrop-filter: blur(12px);
}

.signal-card {
  border-radius: 24px;
  padding: 1.1rem 1.2rem;
}

.signal-label {
  display: block;
  margin-bottom: 0.4rem;
  font-size: 0.82rem;
  color: rgba(27, 26, 24, 0.55);
}

.signal-value {
  font-size: 1.05rem;
}

.signal-value.online {
  color: #136f3a;
}

.signal-value.offline {
  color: #b13a27;
}

.signal-value.static {
  color: #243c73;
}

.panel {
  border-radius: 32px;
  padding: 1.6rem;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
}

.panel h2 {
  font-size: clamp(2.1rem, 4vw, 3rem);
}

.source-pill {
  display: inline-flex;
  align-items: center;
  padding: 0.55rem 0.9rem;
  border-radius: 999px;
  background: #1b1a18;
  color: #fff8f0;
  font-size: 0.82rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
}

.review-form {
  display: grid;
  gap: 1.15rem;
  margin-top: 1.5rem;
}

.field {
  display: grid;
  gap: 0.6rem;
}

.field span,
.field-row span {
  font-size: 0.92rem;
  font-weight: 700;
}

.field-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.field-row small {
  color: rgba(27, 26, 24, 0.58);
}

.field-row small.warning {
  color: #9b4920;
}

input,
textarea {
  width: 100%;
  padding: 0.95rem 1rem;
  border: 1px solid rgba(61, 49, 38, 0.14);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.66);
  color: #1b1a18;
  transition: border-color 160ms ease, transform 160ms ease, box-shadow 160ms ease;
}

input:focus,
textarea:focus {
  outline: none;
  border-color: rgba(155, 73, 32, 0.55);
  box-shadow: 0 0 0 4px rgba(235, 145, 81, 0.14);
  transform: translateY(-1px);
}

textarea {
  resize: vertical;
  min-height: 10rem;
}

.score-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0.75rem;
}

.score-chip {
  display: grid;
  gap: 0.25rem;
  padding: 0.95rem 0.75rem;
  border: 1px solid rgba(61, 49, 38, 0.12);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.72);
  color: #1b1a18;
  cursor: pointer;
  transition: transform 160ms ease, border-color 160ms ease, background 160ms ease;
}

.score-chip strong {
  font-size: 1.15rem;
}

.score-chip small {
  color: rgba(27, 26, 24, 0.55);
}

.score-chip:hover,
.score-chip.active {
  transform: translateY(-2px);
  border-color: rgba(155, 73, 32, 0.48);
  background: linear-gradient(180deg, #fff5eb 0%, #ffe5ca 100%);
}

.message {
  display: grid;
  gap: 0.35rem;
  padding: 0.95rem 1rem;
  border-radius: 18px;
  font-size: 0.95rem;
}

.message.error {
  background: rgba(186, 71, 45, 0.12);
  color: #8d2813;
}

.message.success {
  background: rgba(48, 137, 72, 0.12);
  color: #176232;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  margin-top: 0.25rem;
}

.submit-button {
  min-width: 12rem;
  padding: 1rem 1.4rem;
  border: none;
  border-radius: 999px;
  background: linear-gradient(135deg, #1f3b77 0%, #0f8b6d 100%);
  color: #fff;
  font-weight: 700;
  letter-spacing: 0.03em;
  cursor: pointer;
  transition: transform 160ms ease, opacity 160ms ease, box-shadow 160ms ease;
  box-shadow: 0 14px 30px rgba(15, 77, 118, 0.25);
}

.submit-button:hover:not(:disabled) {
  transform: translateY(-2px);
}

.submit-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  box-shadow: none;
}

.hint {
  margin: 0;
  color: rgba(27, 26, 24, 0.58);
  font-size: 0.92rem;
}

@media (max-width: 980px) {
  .layout {
    grid-template-columns: 1fr;
    padding: 1.5rem 1rem 2rem;
  }

  .hero h1 {
    max-width: 12ch;
  }
}

@media (max-width: 640px) {
  .hero-cards,
  .score-grid {
    grid-template-columns: 1fr;
  }

  .panel {
    padding: 1.2rem;
    border-radius: 24px;
  }

  .actions {
    align-items: stretch;
  }

  .submit-button {
    width: 100%;
  }
}
</style>
