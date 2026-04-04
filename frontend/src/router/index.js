import { createRouter, createWebHistory } from "vue-router";

import InventoryView from "../views/InventoryView.vue";
import ProductView from "../views/ProductView.vue";
import OrderView from "../views/OrderView.vue";
import LogView from "../views/LogView.vue";
import CompanyView from "../views/CompanyView.vue";
import LoginView from "../views/LoginView.vue";

const routes = [
  { path: "/login", component: LoginView },
  { path: "/", component: InventoryView, meta: { requiresAuth: true } },
  { path: "/products", component: ProductView, meta: { requiresAuth: true } },
  { path: "/orders", component: OrderView, meta: { requiresAuth: true } },
  { path: "/logs", component: LogView, meta: { requiresAuth: true } },
  { path: "/companies", component: CompanyView, meta: { requiresAuth: true } }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem("access_token");
  if (to.meta.requiresAuth && !token) {
    next("/login");
    return;
  }
  if (to.path === "/login" && token) {
    next("/");
    return;
  }
  next();
});

export default router;
