<template>
  <div class="min-h-screen overflow-y-auto">

    <!-- ⭐ 컨테이너 통일 -->
    <div class="app-container py-6">

      <div class="panel px-5 py-4 mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <div class="text-xs uppercase tracking-[0.2em] text-slate-500">
            Operations Suite
          </div>
          <h1 class="text-2xl font-semibold text-slate-900">📦 생산 관리 시스템</h1>
        </div>
        <button v-if="showLogout" class="btn btn-secondary" @click="logout">
          로그아웃
        </button>
      </div>

      <nav class="mb-6 flex flex-wrap gap-2 text-slate-700 font-medium">
        <router-link class="btn btn-secondary" to="/">재고</router-link>
        <router-link class="btn btn-secondary" to="/products">상품</router-link>
        <router-link class="btn btn-secondary" to="/orders">주문</router-link>
        <router-link class="btn btn-secondary" to="/companies">거래처</router-link>
      </nav>

    </div>

    <!-- ⭐ 내용도 동일 기준 -->
    <div class="app-container pb-10">
      <router-view />
    </div>

  </div>
</template>

<script setup>
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { signOut } from "firebase/auth";
import { auth } from "./firebase";

const router = useRouter();
const route = useRoute();
const showLogout = computed(() => route.path !== "/login");

const logout = () => {
  signOut(auth).finally(() => {
    router.push("/login");
  });
};
</script>
