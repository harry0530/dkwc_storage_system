import { createRouter, createWebHistory } from "vue-router";

import InventoryView from "../views/InventoryView.vue";
import ProductView from "../views/ProductView.vue";
import OrderView from "../views/OrderView.vue";
import LogView from "../views/LogView.vue";
import CompanyView from "../views/CompanyView.vue";

const routes = [
  { path: "/", component: InventoryView },
  { path: "/products", component: ProductView },
  { path: "/orders", component: OrderView },
  { path: "/logs", component: LogView },
  { path: "/companies", component: CompanyView }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

export default router;