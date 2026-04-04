<template>
  <div class="min-h-screen overflow-y-auto">

    <!-- ⭐ 컨테이너 통일 -->
    <div class="max-w-6xl mx-auto px-6 py-6">

      <h1 class="text-2xl font-bold mb-4">📦 생산 관리 시스템</h1>

      <nav class="mb-6 flex gap-4 text-blue-600 font-medium">
        <router-link to="/">재고</router-link>
        <router-link to="/products">상품</router-link>
        <router-link to="/orders">주문</router-link>
        <router-link to="/companies">거래처</router-link>
      </nav>

    </div>

    <!-- ⭐ 내용도 동일 기준 -->
    <div class="max-w-6xl mx-auto px-6 pb-8">
      <router-view />
    </div>

  </div>
</template>
