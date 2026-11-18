<template>
  <div class="min-h-screen">
    <header class="site-header">
      <div class="app-container flex min-h-[76px] items-center justify-between gap-5">
        <router-link to="/" class="brand-lockup" aria-label="동광 생산관리 홈">
          <span class="brand-mark" aria-hidden="true"><span class="brand-mark-line"></span></span>
          <span>
            <strong class="brand-name">DONGKWANG</strong>
            <span class="brand-subtitle">Manufacturing Operations</span>
          </span>
        </router-link>
        <div v-if="showLogout" class="hidden items-center gap-3 sm:flex">
          <span class="header-status"><i></i> 운영 시스템</span>
          <button class="header-logout" @click="logout">로그아웃</button>
        </div>
      </div>
      <nav v-if="showLogout" class="primary-nav" aria-label="주 메뉴">
        <div class="app-container flex items-center gap-1 overflow-x-auto">
          <router-link to="/">단품 재고</router-link>
          <router-link to="/finished-inventory">완제품 재고</router-link>
          <router-link to="/products">완제품 관리</router-link>
          <router-link to="/orders">주문·발주</router-link>
          <router-link to="/companies">거래처</router-link>
          <router-link to="/logs">입출고 이력</router-link>
        </div>
      </nav>
    </header>

    <main :class="showLogout ? 'app-container py-8' : 'login-shell'"><router-view /></main>

    <footer v-if="showLogout" class="app-footer">
      <div class="app-container flex flex-wrap items-center justify-between gap-2">
        <span>DONGKWANG MFG · Production Management System</span>
        <span>경기도 화성시 향남읍 토성로 296-5</span>
      </div>
    </footer>
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
const logout = () => signOut(auth).finally(() => router.push("/login"));
</script>
