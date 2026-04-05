<script setup>
import { ref, onMounted, computed } from "vue";
import api from "../api";

const orders = ref([]);
const products = ref([]);
const companies = ref([]);
const aliases = ref([]);
const boms = ref([]);
const inventory = ref([]);

const companyInput = ref("");
const selectedCompany = ref("");

const codeInput = ref("");
const selectedCode = ref("");

const quantity = ref("");

// 표시
const displayProduct = ref("");
const stockWarning = ref("");

// ⭐ 공통 문자열 정리 함수 (핵심)
const clean = (v) => (v || "").trim().toLowerCase();

// =====================
// 데이터 로드
// =====================
const loadAll = async () => {
  const o = await api.get("/orders/");
  const p = await api.get("/products/");
  const c = await api.get("/companies/");
  const a = await api.get("/product-alias/");
  const b = await api.get("/bom/");
  const i = await api.get("/inventory/");

  orders.value = o.data;
  products.value = p.data;
  companies.value = c.data;
  aliases.value = a.data;
  boms.value = b.data;
  inventory.value = i.data;
};

// =====================
// 제품 표시 + 재고 체크 (🔥 전부 수정됨)
// =====================
const updateProductName = () => {
  const inputCode = selectedCode.value || codeInput.value;

  if (!inputCode) {
    displayProduct.value = "";
    stockWarning.value = "";
    return;
  }

  const cleanInput = clean(inputCode);

  // ⭐ alias 찾기
  const alias = aliases.value.find(a =>
    a.company === selectedCompany.value &&
    clean(a.alias_code) === cleanInput
  );

  let realCode = inputCode;
  if (alias) realCode = alias.product_code;

  const cleanReal = clean(realCode);

  // ⭐ 제품 찾기
  const product = products.value.find(p =>
    clean(p.code) === cleanReal
  );

  if (!product) {
    displayProduct.value = "❌ 없는 제품";
    stockWarning.value = "";
    return;
  }

  // 표시
  displayProduct.value = alias
    ? `${inputCode} → ${realCode} (${product.name})`
    : `${realCode} (${product.name})`;

  // ⭐ BOM 찾기
  const relatedBOM = boms.value.filter(b =>
    clean(b.parent_code) === cleanReal
  );

  let warnings = [];

  for (const bom of relatedBOM) {

    // ⭐ inventory 매칭
    const inv = inventory.value.find(i =>
      clean(i.product_code || i.code) === clean(bom.child_code)
    );

    const required = bom.quantity * (Number(quantity.value) || 0);
    const current = inv ? inv.quantity : 0;

    if (required > current) {
      warnings.push(
        `${bom.child_code} 부족 (필요:${required} / 현재:${current})`
      );
    }
  }

  stockWarning.value = warnings.join(" | ");
};

// =====================
// 회사 자동완성
// =====================
const showCompanyDropdown = ref(false);

const filteredCompanies = computed(() =>
  companies.value.filter(c =>
    c.name.includes(companyInput.value)
  )
);

const selectCompany = (name) => {
  selectedCompany.value = name;
  companyInput.value = name;
  showCompanyDropdown.value = false;

  updateProductName();
};

// =====================
// 품번 자동완성
// =====================
const showCodeDropdown = ref(false);

const filteredCodes = computed(() =>
  aliases.value.filter(a =>
    a.company === selectedCompany.value &&
    a.alias_code.includes(codeInput.value)
  )
);

const selectCode = (code) => {
  selectedCode.value = code;
  codeInput.value = code;
  showCodeDropdown.value = false;

  updateProductName();
};

// =====================
// 주문 생성
// =====================
const createOrder = async () => {
  if (!selectedCompany.value || !quantity.value) return;

  if (stockWarning.value) {
    alert("재고 부족 상태입니다!");
    return;
  }

  const finalCode = selectedCode.value || codeInput.value;

  if (!finalCode) return alert("품번 입력");

  await api.post("/orders/", {
    product_code: finalCode,
    quantity: Number(quantity.value),
    company: selectedCompany.value
  });

  // 초기화
  companyInput.value = "";
  codeInput.value = "";
  selectedCode.value = "";
  displayProduct.value = "";
  stockWarning.value = "";
  quantity.value = "";

  loadAll();
};

// =====================
// 생산 / 취소
// =====================
const runProduction = async (id) => {
  await api.post(`/orders/produce/${id}`);
  loadAll();
};

const undoProduction = async (id) => {
  await api.post(`/orders/undo/${id}`);
  loadAll();
};

onMounted(loadAll);

// =====================
// 재고 현황 PDF/프린트
// =====================
const inventoryReportRows = computed(() => {
  return inventory.value
    .map((inv) => {
      const code = inv.product_code || inv.code || "";
      const product = products.value.find(
        (p) => clean(p.code) === clean(code)
      );
      return {
        code,
        name: product ? product.name : "",
        quantity: Number(inv.quantity || 0)
      };
    })
    .sort((a, b) => a.code.localeCompare(b.code));
});

const buildInventoryReportHtml = (modeLabel) => {
  const timestamp = new Date().toLocaleString("ko-KR");
  const rows = inventoryReportRows.value
    .map(
      (r, i) => `
        <tr>
          <td>${i + 1}</td>
          <td>${r.code}</td>
          <td>${r.name || "-"}</td>
          <td class="qty">${r.quantity}</td>
        </tr>`
    )
    .join("");

  return `<!doctype html>
  <html lang="ko">
    <head>
      <meta charset="utf-8" />
      <title>재고 현황 - ${modeLabel}</title>
      <style>
        body { font-family: Arial, sans-serif; color: #111; padding: 24px; }
        h1 { font-size: 20px; margin: 0 0 8px; }
        .meta { font-size: 12px; color: #555; margin-bottom: 16px; }
        table { width: 100%; border-collapse: collapse; font-size: 12px; }
        th, td { border: 1px solid #ddd; padding: 6px 8px; text-align: left; }
        th { background: #f5f5f5; }
        td.qty { text-align: right; }
        .note { font-size: 11px; color: #666; margin-top: 12px; }
      </style>
    </head>
    <body>
      <h1>재고 현황</h1>
      <div class="meta">생성일시: ${timestamp}</div>
      <table>
        <thead>
          <tr>
            <th>No</th>
            <th>품번</th>
            <th>제품명</th>
            <th>재고</th>
          </tr>
        </thead>
        <tbody>
          ${rows || `<tr><td colspan="4">재고 데이터가 없습니다.</td></tr>`}
        </tbody>
      </table>
      <div class="note">PDF 저장은 인쇄 대화상자에서 "PDF로 저장"을 선택하세요.</div>
      <script>
        window.onload = () => { window.focus(); window.print(); };
        window.onafterprint = () => { window.close(); };
      <\\/script>
    </body>
  </html>`;
};

const openInventoryPrintWindow = (mode) => {
  const modeLabel = mode === "pdf" ? "PDF 저장" : "프린트";
  const popup = window.open("", "_blank");
  if (!popup) {
    alert("팝업이 차단되어 재고 현황을 열 수 없습니다.");
    return;
  }
  popup.document.open();
  popup.document.write(buildInventoryReportHtml(modeLabel));
  popup.document.close();
};

const saveInventoryPdf = () => openInventoryPrintWindow("pdf");
const printInventory = () => openInventoryPrintWindow("print");
</script>

<template>
  <div>

    <div class="flex items-center justify-between mb-6">
      <h2 class="text-3xl font-bold">📋 주문 관리</h2>
      <div class="flex gap-2">
        <button
          @click="saveInventoryPdf"
          class="bg-indigo-600 text-white px-3 h-9 rounded text-sm"
        >
          재고 PDF 저장
        </button>
        <button
          @click="printInventory"
          class="bg-gray-700 text-white px-3 h-9 rounded text-sm"
        >
          재고 프린트
        </button>
      </div>
    </div>

    <div class="bg-white shadow rounded-xl p-3 mb-6 flex gap-3 items-center">

      <div class="relative w-40">
        <input
          v-model="companyInput"
          @input="updateProductName"
          @focus="showCompanyDropdown = true"
          @blur="setTimeout(() => showCompanyDropdown = false, 200)"
          placeholder="회사"
          class="border px-3 py-1 h-9 rounded w-full text-sm"
        />
        <div v-if="showCompanyDropdown"
          class="absolute bg-white border w-full z-10 max-h-40 overflow-y-auto">
          <div v-for="c in filteredCompanies"
            :key="c.id"
            @click="selectCompany(c.name)"
            class="p-2 hover:bg-gray-100 cursor-pointer">
            {{ c.name }}
          </div>
        </div>
      </div>

      <div class="relative w-40">
        <input
          v-model="codeInput"
          @input="updateProductName"
          @focus="showCodeDropdown = true"
          @blur="setTimeout(() => showCodeDropdown = false, 200)"
          placeholder="품번"
          class="border px-3 py-1 h-9 rounded w-full text-sm"
        />
        <div v-if="showCodeDropdown"
          class="absolute bg-white border w-full z-10 max-h-40 overflow-y-auto">
          <div v-for="a in filteredCodes"
            :key="a.id"
            @click="selectCode(a.alias_code)"
            class="p-2 hover:bg-gray-100 cursor-pointer">
            {{ a.alias_code }}
          </div>
        </div>
      </div>

      <div class="text-sm text-gray-700 w-64">
        {{ displayProduct }}
      </div>

      <input v-model="quantity"
        @input="updateProductName"
        type="number"
        min="1"
        placeholder="수량"
        class="border px-3 py-1 h-9 rounded w-24 text-sm text-gray-900" />

      <button @click="createOrder"
        class="bg-blue-500 text-white px-4 h-9 rounded">
        주문 생성
      </button>

    </div>

    <div v-if="stockWarning"
      class="text-red-500 text-sm mb-4">
      ⚠ {{ stockWarning }}
    </div>

    <div class="bg-white shadow rounded-xl overflow-hidden">
      <table class="w-full text-left">

        <thead class="bg-gray-100">
          <tr>
            <th class="p-3">ID</th>
            <th class="p-3">제품</th>
            <th class="p-3">수량</th>
            <th class="p-3">회사</th>
            <th class="p-3">상태</th>
            <th class="p-3">작업</th>
          </tr>
        </thead>

        <tbody>
          <tr v-for="o in orders" :key="o.id" class="border-t">

            <td class="p-3">{{ o.id }}</td>

            <td class="p-3">
              {{ o.product_name }}
              <div class="text-xs text-gray-400">
                {{ o.product_code }}
              </div>
            </td>

            <td class="p-3">{{ o.quantity }}</td>
            <td class="p-3">{{ o.company }}</td>

            <td class="p-3">
              <span v-if="o.status === 'WAIT'">대기</span>
              <span v-else>완료</span>
            </td>

            <td class="p-3 flex gap-2">
              <button v-if="o.status === 'WAIT'"
                @click="runProduction(o.id)"
                class="bg-green-500 text-white px-2 py-1 text-sm rounded">
                생산
              </button>

              <button v-if="o.status === 'DONE'"
                @click="undoProduction(o.id)"
                class="bg-red-500 text-white px-2 py-1 text-sm rounded">
                취소
              </button>
            </td>

          </tr>
        </tbody>

      </table>
    </div>

    <div class="bg-white shadow rounded-xl overflow-hidden mt-6">
      <div class="p-3 border-b font-semibold">재고 현황</div>
      <table class="w-full text-left">
        <thead class="bg-gray-100">
          <tr>
            <th class="p-3">No</th>
            <th class="p-3">품번</th>
            <th class="p-3">제품명</th>
            <th class="p-3 text-right">재고</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(row, i) in inventoryReportRows"
            :key="`${row.code}-${i}`"
            class="border-t"
          >
            <td class="p-3">{{ i + 1 }}</td>
            <td class="p-3">{{ row.code }}</td>
            <td class="p-3">{{ row.name || "-" }}</td>
            <td class="p-3 text-right">{{ row.quantity }}</td>
          </tr>
          <tr v-if="inventoryReportRows.length === 0" class="border-t">
            <td class="p-3" colspan="4">재고 데이터가 없습니다.</td>
          </tr>
        </tbody>
      </table>
    </div>

  </div>
</template>
