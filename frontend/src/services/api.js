const defaultHeaders = {
  "Content-Type": "application/json",
};

async function parseJsonSafely(response) {
  const text = await response.text();
  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function messageFromPayload(payload, fallback) {
  if (!payload) {
    return fallback;
  }

  if (typeof payload === "string") {
    return payload;
  }

  if (typeof payload.detail === "string") {
    return payload.detail;
  }

  if (Array.isArray(payload.detail)) {
    return payload.detail
      .map((item) => item.msg || item.message || "Invalid field")
      .join("; ");
  }

  if (typeof payload.message === "string") {
    return payload.message;
  }

  return fallback;
}

async function request(path, options = {}) {
  const { timeoutMs, ...fetchOptions } = options;
  const controller = timeoutMs ? new AbortController() : null;
  const timeoutId = timeoutMs
    ? window.setTimeout(() => controller.abort(), timeoutMs)
    : null;

  let response;
  let payload;

  try {
    response = await fetch(`/api${path}`, {
      ...fetchOptions,
      signal: controller?.signal || fetchOptions.signal,
    });
    payload = await parseJsonSafely(response);
  } catch (error) {
    if (error?.name === "AbortError") {
      const timeoutError = new Error("Analytics request timed out. Showing the last snapshot.");
      timeoutError.status = 408;
      throw timeoutError;
    }
    throw error;
  } finally {
    if (timeoutId) {
      window.clearTimeout(timeoutId);
    }
  }

  if (!response.ok) {
    const error = new Error(messageFromPayload(payload, response.statusText || "Request failed"));
    error.status = response.status;
    error.payload = payload;
    throw error;
  }

  return payload;
}

function queryString(params) {
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      searchParams.set(key, String(value));
    }
  });

  const query = searchParams.toString();
  return query ? `?${query}` : "";
}

export function getHealth() {
  return request("/health");
}

export function getProducts() {
  return request("/products");
}

export function getProduct(productId) {
  return request(`/products/${encodeURIComponent(productId)}`);
}

export function submitProductReview(productId, payload) {
  return request(`/products/${encodeURIComponent(productId)}/reviews`, {
    method: "POST",
    headers: defaultHeaders,
    body: JSON.stringify(payload),
  });
}

export function getDashboard({
  preferCache = true,
  allowSample = true,
  timeoutMs = 8000,
} = {}) {
  return request(
    `/analytics/dashboard${queryString({
      prefer_cache: preferCache,
      allow_sample: allowSample,
    })}`,
    { timeoutMs }
  );
}

export function getRecentReviews(limit = 20) {
  return request(`/analytics/recent${queryString({ limit })}`);
}

export function getOpinions({ limit = 50, sentiment = undefined } = {}) {
  return request(`/analytics/opinions${queryString({ limit, sentiment })}`);
}
