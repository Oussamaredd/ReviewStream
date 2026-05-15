import { createRouter, createWebHistory } from "vue-router";

import AnalyticsPage from "../pages/AnalyticsPage.vue";
import ProductsPage from "../pages/ProductsPage.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      redirect: "/products",
    },
    {
      path: "/products",
      name: "products",
      component: ProductsPage,
    },
    {
      path: "/analytics",
      name: "analytics",
      component: AnalyticsPage,
    },
    {
      path: "/dashboard",
      redirect: "/analytics",
    },
  ],
});

export default router;
