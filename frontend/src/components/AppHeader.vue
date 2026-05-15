<template>
  <header class="app-header">
    <RouterLink class="brand-link" to="/products" aria-label="ReviewStream products">
      <span class="brand-mark">RS</span>
      <span>ReviewStream</span>
    </RouterLink>

    <nav class="main-nav" aria-label="Primary navigation">
      <RouterLink to="/products">Products</RouterLink>
      <RouterLink to="/analytics">Analytics</RouterLink>
    </nav>
  </header>
</template>
