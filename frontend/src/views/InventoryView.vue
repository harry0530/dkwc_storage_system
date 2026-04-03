<script setup>
import { ref, onMounted, computed } from "vue";
import api from "../api";

const inventory = ref([]);
const searchCode = ref("");

const code = ref("");
const quantity = ref("");

// 로그
const selectedProduct = ref("");
const productLogs = ref([]);

// =====================
// 데이터 로드
// =====================
const loadInventory = async () => {
  const res = await api.get("/inventory/");
  inventory.value = res.data;
};

// =====================
// 입고
// =====================
const addStock = async () => {
  if (!code.value || !quantity.value) return;

  await api.post("/inventory/", {
    product_code: code.value,
    quantity: Number(quantity.value)
  });

  code.value = "";
  quantity.value = "";

  loadInventory();
};

// =====================
// 로그 불러오기
// =====================
const loadProductLogs = async (productCode) => {
  console.log("clicked:", productCode); // ⭐ 확인용

  const res = await api.get("/transactions/");

  productLogs.value = res.data.filter(
    (log) =>
      log.product_code &&
      log.product_code.toLowerCase() === productCode.toLowerCase()
  );

  selectedProduct.value = productCode;
};

const parseUtcDate = (dateValue) => {
  if (!dateValue) return null;
  const raw = String(dateValue).trim();
  const normalized = raw.includes("T") ? raw : raw.replace(" ", "T");
  const withTimezone = /[zZ]|[+\-]\d{2}:\d{2}$/.test(normalized)
    ? normalized
    : `${normalized}Z`;
  const date = new Date(withTimezone);
  return Number.isNaN(date.getTime()) ? null : date;
};

const formatKst = (dateValue) => {
  const date = parseUtcDate(dateValue);
  if (!date) return "-";
  return new Intl.DateTimeFormat("ko-KR", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false
  }).format(date);
};

const formatReason = (log) => {
  if (!log?.reason) return "-";

  if (log.reason === "PRODUCTION" && log.type === "IN") return "입고 생산";
  if (log.reason === "PRODUCTION" && log.type === "OUT") return "생산 출고";
  if (log.reason === "STOCK_IN") return "입고";
  if (log.reason === "UNDO_PRODUCTION") return "생산 취소";
  if (log.reason === "SHIPMENT") return "출하";

  return log.reason;
};

const lowStockItems = computed(() =>
  inventory.value.filter((item) => Number(item.quantity) < Number(item.min_stock))
);

const filteredInventory = computed(() => {
  const keyword = (searchCode.value || "").trim().toLowerCase();
  if (!keyword) return inventory.value;
  return inventory.value.filter((item) =>
    (item.code || "").toLowerCase().includes(keyword)
  );
});

onMounted(loadInventory);
</script>

<template>
  <div>

    <h2 class="text-3xl font-bold mb-6">📦 재고 관리</h2>

    <!-- 입력 -->
    <div class="bg-white shadow rounded-xl p-3 mb-6 flex gap-2 items-center">

      <input v-model="code"
        placeholder="품번"
        class="border px-3 py-1 h-9 rounded text-sm w-40" />

      <input v-model="quantity"
        type="number"
        placeholder="수량"
        class="border px-3 py-1 h-9 rounded text-sm w-24" />

      <button @click="addStock"
        class="bg-blue-500 text-white px-4 h-9 rounded text-sm">
        입고
      </button>

      <input v-model="searchCode"
        placeholder="품번 검색"
        class="border px-3 py-1 h-9 rounded text-sm w-48 ml-auto" />

    </div>

    <!-- 재고 부족 -->
    <div
      v-if="lowStockItems.length"
      class="mb-4 p-3 bg-red-100 text-red-700 rounded"
    >
      ⚠️ 재고 부족 항목이 있습니다
      <div class="mt-2 text-sm">
        <div
          v-for="item in lowStockItems"
          :key="`low-${item.code}`"
        >
          - {{ item.name || "이름없음" }} ({{ item.code }}) :
          {{ item.min_stock - item.quantity }}개 부족
        </div>
      </div>
    </div>

    <!-- 재고 테이블 -->
    <div class="bg-white shadow rounded-xl overflow-hidden">
      <table class="w-full text-left">

        <thead class="bg-gray-100">
          <tr>
            <th class="p-3">제품</th>
            <th class="p-3">위치</th>
            <th class="p-3">현재 재고</th>
            <th class="p-3">최소 재고</th>
          </tr>
        </thead>

        <tbody>
          <tr
            v-for="item in filteredInventory"
            :key="item.code"
            class="border-t hover:bg-gray-100"
          >

            <!-- ⭐ 클릭은 여기(td)에 걸어야 함 -->
            <td class="p-3 cursor-pointer"
                @click="loadProductLogs(item.code)">
              <div class="font-semibold">{{ item.name }}</div>
              <div class="text-xs text-gray-400">{{ item.code }}</div>
            </td>

            <td class="p-3">{{ item.location }}</td>

            <td class="p-3 font-bold"
                :class="item.quantity < item.min_stock ? 'text-red-500' : 'text-blue-600'">
              {{ item.quantity }}
            </td>

            <td class="p-3">{{ item.min_stock }}</td>

          </tr>
        </tbody>

      </table>

      <div
        v-if="filteredInventory.length === 0"
        class="p-4 text-sm text-gray-500"
      >
        검색 결과가 없습니다.
      </div>
    </div>

    <!-- 로그 -->
    <div v-if="selectedProduct" class="mt-8">

      <h3 class="text-xl font-bold mb-3">
        📊 {{ selectedProduct }} 로그
      </h3>

      <div class="bg-white shadow rounded-xl overflow-hidden">
        <table class="w-full text-left">

          <thead class="bg-gray-100">
            <tr>
              <th class="p-3">시간</th>
              <th class="p-3">수량</th>
              <th class="p-3">타입</th>
              <th class="p-3">이유</th>
            </tr>
          </thead>

          <tbody>
            <tr v-for="log in productLogs"
                :key="log.id"
                class="border-t">

              <td class="p-3">
                {{ formatKst(log.created_at) }}
              </td>

              <td class="p-3">
                <span :class="log.type === 'OUT' ? 'text-red-500' : 'text-green-500'">
                  {{ log.type === 'OUT' ? '-' : '+' }}{{ log.quantity }}
                </span>
              </td>

              <td class="p-3">
                <span v-if="log.type === 'OUT'" class="text-red-500 font-bold">출고</span>
                <span v-else class="text-green-500 font-bold">입고</span>
              </td>

              <td class="p-3 text-gray-600">
                {{ formatReason(log) }}
              </td>

            </tr>

            <!-- 로그 없을 때 -->
            <tr v-if="productLogs.length === 0">
              <td colspan="4" class="p-3 text-center text-gray-400">
                로그 없음
              </td>
            </tr>

          </tbody>

        </table>
      </div>

    </div>

  </div>
</template>
