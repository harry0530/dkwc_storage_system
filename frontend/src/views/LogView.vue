<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import api from "../api";

const logs = ref([]);
const loading = ref(false);
const error = ref("");
const search = ref("");
const typeFilter = ref("");
const startDate = ref("");
const endDate = ref("");
const page = ref(1);
const pageSize = ref(30);
const total = ref(0);
const totalPages = ref(1);
const summary = ref({ total: 0, in_count: 0, out_count: 0, in_quantity: 0, out_quantity: 0 });
const legacyLogs = ref(null);
let searchTimer;

const number = new Intl.NumberFormat("ko-KR");
const pageNumbers = computed(() => {
  const start = Math.max(1, Math.min(page.value - 2, totalPages.value - 4));
  const end = Math.min(totalPages.value, start + 4);
  return Array.from({ length: Math.max(0, end - start + 1) }, (_, index) => start + index);
});

const applyLegacyFilters = () => {
  const term = search.value.trim().toLocaleLowerCase("ko-KR");
  const filtered = (legacyLogs.value || []).filter((log) => {
    const matchesSearch = !term || [log.product_code, log.product_name, log.company]
      .some((value) => String(value || "").toLocaleLowerCase("ko-KR").includes(term));
    const matchesType = !typeFilter.value || log.type === typeFilter.value;
    const date = String(log.created_at || "").slice(0, 10);
    const matchesStart = !startDate.value || date >= startDate.value;
    const matchesEnd = !endDate.value || date <= endDate.value;
    return matchesSearch && matchesType && matchesStart && matchesEnd;
  });

  total.value = filtered.length;
  totalPages.value = Math.max(1, Math.ceil(filtered.length / pageSize.value));
  if (page.value > totalPages.value) page.value = totalPages.value;
  const offset = (page.value - 1) * pageSize.value;
  logs.value = filtered.slice(offset, offset + pageSize.value);
  summary.value = filtered.reduce((acc, log) => {
    acc.total += 1;
    if (log.type === "IN") {
      acc.in_count += 1;
      acc.in_quantity += Number(log.quantity || 0);
    } else if (log.type === "OUT") {
      acc.out_count += 1;
      acc.out_quantity += Number(log.quantity || 0);
    }
    return acc;
  }, { total: 0, in_count: 0, out_count: 0, in_quantity: 0, out_quantity: 0 });
};

const loadLegacyHistory = async () => {
  if (!legacyLogs.value) {
    const { data } = await api.get("/transactions/");
    legacyLogs.value = data
      .map((log) => ({ ...log, company: null }))
      .sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)) || b.id - a.id);
  }
  applyLegacyFilters();
};

const loadLogs = async () => {
  loading.value = true;
  error.value = "";
  try {
    const { data } = await api.get("/transactions/history", {
      params: {
        page: page.value,
        page_size: pageSize.value,
        search: search.value.trim() || undefined,
        type: typeFilter.value || undefined,
        start_date: startDate.value || undefined,
        end_date: endDate.value || undefined
      }
    });
    logs.value = data.items;
    total.value = data.total;
    totalPages.value = data.total_pages;
    summary.value = data.summary;
  } catch (requestError) {
    if (requestError?.response?.status === 404) {
      try {
        await loadLegacyHistory();
        return;
      } catch (legacyError) {
        error.value = legacyError?.response?.data?.detail || "입출고 이력을 불러오지 못했습니다.";
      }
    } else {
      error.value = requestError?.response?.data?.detail || "입출고 이력을 불러오지 못했습니다.";
    }
  } finally {
    loading.value = false;
  }
};

const parseUtcDate = (value) => {
  if (!value) return null;
  const raw = String(value).trim();
  const normalized = raw.includes("T") ? raw : raw.replace(" ", "T");
  const withTimezone = /[zZ]|[+\-]\d{2}:\d{2}$/.test(normalized) ? normalized : `${normalized}Z`;
  const parsed = new Date(withTimezone);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
};
const formatDate = (value) => {
  const parsed = parseUtcDate(value);
  if (!parsed) return "-";
  return new Intl.DateTimeFormat("ko-KR", { timeZone: "Asia/Seoul", year: "numeric", month: "2-digit", day: "2-digit" }).format(parsed);
};
const formatReason = (log) => {
  if (String(log.reason || "").startsWith("HISTORICAL_")) {
    return log.type === "IN" ? "발주 입고" : "재고 출고";
  }
  const labels = {
    PRODUCTION: log.type === "IN" ? "생산 입고" : "생산 출고",
    STOCK_IN: "일반 입고", UNDO_PRODUCTION: "생산 취소", SHIPMENT: "출하",
    PURCHASE_IN: "발주 입고", PURCHASE_EDIT: "발주 수정", PURCHASE_DELETE: "발주 삭제",
    PURCHASE_BATCH_DELETE: "발주 일괄 삭제", STOCK_OUT: "재고 출고"
  };
  return labels[log.reason] || log.reason || "-";
};
const goToPage = (target) => {
  if (target < 1 || target > totalPages.value || target === page.value) return;
  page.value = target;
  if (legacyLogs.value) applyLegacyFilters();
  else loadLogs();
};
const resetFilters = () => {
  search.value = ""; typeFilter.value = ""; startDate.value = ""; endDate.value = "";
  page.value = 1; loadLogs();
};

watch([typeFilter, startDate, endDate, pageSize], () => { page.value = 1; loadLogs(); });
watch(search, () => {
  window.clearTimeout(searchTimer);
  searchTimer = window.setTimeout(() => { page.value = 1; loadLogs(); }, 350);
});
onMounted(loadLogs);
onBeforeUnmount(() => window.clearTimeout(searchTimer));
</script>

<template>
  <section>
    <div class="page-heading">
      <div>
        <p class="eyebrow">Inventory Movement</p>
        <h1 class="page-title">입출고 이력</h1>
        <p class="page-description">발주와 생산 과정에서 발생한 입출고 기록을 기간별로 조회합니다.</p>
      </div>
      <span class="history-period">2013 — 현재</span>
    </div>

    <div class="metric-grid">
      <article class="metric-card metric-total"><span>조회 기록</span><strong>{{ number.format(summary.total) }}</strong><small>현재 필터 기준</small></article>
      <article class="metric-card metric-in"><span>입고 건수</span><strong>{{ number.format(summary.in_count) }}</strong><small>총 {{ number.format(summary.in_quantity) }}개</small></article>
      <article class="metric-card metric-out"><span>출고 건수</span><strong>{{ number.format(summary.out_count) }}</strong><small>총 {{ number.format(summary.out_quantity) }}개</small></article>
    </div>

    <div class="history-filter panel">
      <div class="filter-search">
        <label for="history-search">통합 검색</label>
        <div class="search-input-wrap">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m21 21-4.35-4.35m2.35-5.65a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z" /></svg>
          <input id="history-search" v-model="search" class="input" placeholder="품번, 제품명, 거래처" />
        </div>
      </div>
      <div><label for="history-type">구분</label><select id="history-type" v-model="typeFilter" class="input"><option value="">전체</option><option value="IN">입고</option><option value="OUT">출고</option></select></div>
      <div><label for="history-start">시작일</label><input id="history-start" v-model="startDate" type="date" class="input" /></div>
      <div><label for="history-end">종료일</label><input id="history-end" v-model="endDate" type="date" class="input" /></div>
      <button class="btn btn-secondary" type="button" @click="resetFilters">초기화</button>
    </div>

    <div v-if="error" class="error-banner">{{ error }}</div>
    <div class="history-table panel">
      <div class="table-toolbar">
        <div><strong>{{ number.format(total) }}</strong>건의 기록</div>
        <select v-model.number="pageSize" class="input" aria-label="페이지당 표시 개수"><option :value="30">30개씩</option><option :value="50">50개씩</option><option :value="100">100개씩</option></select>
      </div>
      <div class="overflow-x-auto">
        <table class="data-table">
          <thead><tr><th>처리일</th><th>구분</th><th>품목</th><th class="text-right">수량</th><th>거래처</th><th>처리 내용</th></tr></thead>
          <tbody>
            <tr v-if="loading"><td colspan="6" class="table-state"><span class="loading-ring"></span> 이력을 불러오는 중입니다.</td></tr>
            <tr v-else-if="!logs.length"><td colspan="6" class="table-state">조건에 맞는 입출고 기록이 없습니다.</td></tr>
            <tr v-for="log in logs" v-else :key="log.id">
              <td class="date-cell">{{ formatDate(log.created_at) }}</td>
              <td><span :class="['movement-badge', log.type === 'IN' ? 'is-in' : 'is-out']">{{ log.type === "IN" ? "입고" : "출고" }}</span></td>
              <td><div class="product-name">{{ log.product_name || "품목명 미등록" }}</div><div class="product-code">{{ log.product_code }}</div></td>
              <td class="quantity-cell" :class="log.type === 'IN' ? 'quantity-in' : 'quantity-out'">{{ log.type === "IN" ? "+" : "−" }}{{ number.format(log.quantity) }}</td>
              <td>{{ log.company || "-" }}</td>
              <td>{{ formatReason(log) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="pagination-bar">
        <span>{{ number.format((page - 1) * pageSize + (logs.length ? 1 : 0)) }}–{{ number.format((page - 1) * pageSize + logs.length) }} / {{ number.format(total) }}</span>
        <div class="pagination-buttons"><button :disabled="page === 1" @click="goToPage(page - 1)">이전</button><button v-for="item in pageNumbers" :key="item" :class="{ active: item === page }" @click="goToPage(item)">{{ item }}</button><button :disabled="page === totalPages" @click="goToPage(page + 1)">다음</button></div>
      </div>
    </div>
  </section>
</template>
