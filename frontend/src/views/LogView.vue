<script setup>
import { ref, onMounted, computed } from "vue";
import api from "../api";

const logs = ref([]);

const search = ref("");
const typeFilter = ref("");
const dateFilter = ref("");

// =====================
// 데이터 로드
// =====================
const loadLogs = async () => {
  const res = await api.get("/transactions/");
  logs.value = res.data;
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

// 날짜 포맷
const formatDate = (dateStr) => {
  const date = parseUtcDate(dateStr);
  if (!date) return "-";
  return new Intl.DateTimeFormat("ko-KR", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    hour12: false
  }).format(date);
};

const formatKstDate = (dateStr) => {
  const date = parseUtcDate(dateStr);
  if (!date) return "";
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "2-digit",
    day: "2-digit"
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

// =====================
// 필터
// =====================
const filteredLogs = computed(() => {
  return logs.value.filter((log) => {

    const matchSearch =
      log.product_code?.includes(search.value) ||
      log.product_name?.includes(search.value);

    const matchType =
      !typeFilter.value || log.type === typeFilter.value;

    const matchDate =
      !dateFilter.value ||
      formatKstDate(log.created_at) === dateFilter.value;

    return matchSearch && matchType && matchDate;
  });
});

onMounted(loadLogs);
</script>

<template>
  <div>

    <h2 class="text-3xl font-bold mb-6">📦 재고 로그</h2>

    <!-- 필터 -->
    <div class="bg-white shadow rounded-xl p-3 mb-6 flex gap-3 items-center">

      <input
        v-model="search"
        placeholder="제품명 / 품번 검색"
        class="border px-3 py-1 rounded h-9 w-60 text-sm"
      />

      <select v-model="typeFilter"
        class="border px-2 py-1 rounded h-9 text-sm">
        <option value="">전체</option>
        <option value="IN">입고</option>
        <option value="OUT">출고</option>
      </select>

      <input
        v-model="dateFilter"
        type="date"
        class="border px-2 py-1 rounded h-9 text-sm"
      />

    </div>

    <!-- 테이블 -->
    <div class="bg-white shadow rounded-xl overflow-hidden">
      <table class="w-full text-left">

        <thead class="bg-gray-100">
          <tr>
            <th class="p-3">시간</th>
            <th class="p-3">제품</th>
            <th class="p-3">수량</th>
            <th class="p-3">타입</th>
            <th class="p-3">이유</th>
          </tr>
        </thead>

        <tbody>
          <tr
            v-for="log in filteredLogs"
            :key="log.id"
            class="border-t hover:bg-gray-50"
          >

            <!-- 시간 -->
            <td class="p-3">
              {{ formatDate(log.created_at) }}
            </td>

            <!-- 제품 -->
            <td class="p-3">
              <div class="font-semibold">
                {{ log.product_name || "-" }}
              </div>
              <div class="text-xs text-gray-400">
                {{ log.product_code }}
              </div>
            </td>

            <!-- 수량 -->
            <td class="p-3">
              <span :class="log.type === 'OUT' ? 'text-red-500' : 'text-green-500'">
                {{ log.type === 'OUT' ? '-' : '+' }}{{ log.quantity }}
              </span>
            </td>

            <!-- 타입 -->
            <td class="p-3">
              <span v-if="log.type === 'OUT'" class="text-red-500 font-bold">
                출고
              </span>
              <span v-else class="text-green-500 font-bold">
                입고
              </span>
            </td>

            <!-- 이유 -->
            <td class="p-3 text-gray-600">
              {{ formatReason(log) }}
            </td>

          </tr>
        </tbody>

      </table>
    </div>

  </div>
</template>
