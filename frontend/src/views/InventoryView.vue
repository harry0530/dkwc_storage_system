<script setup>
import { ref, onMounted, computed, watch } from "vue";
import api from "../api";
import * as XLSX from "xlsx";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";

const inventory = ref([]);
const products = ref([]);
const searchCode = ref("");
const searchNameInput = ref("");
const showNameDropdown = ref(false);
const typeFilter = ref("PART");

const code = ref("");
const nameInput = ref("");
const quantity = ref("");
const showAddNameDropdown = ref(false);
const showAddCodeDropdown = ref(false);

// 수정
const editingCode = ref("");
const editName = ref("");
const editLocation = ref("");
const editMinStock = ref("");
const editQuantity = ref("");
const editReason = ref("");

// 부품 품번 구성
const partFirst = ref("1");
const partTwo = ref("01");
const partMid = ref("M");
const partDigit = ref("1");
const partLast = ref("S");

// 검색용 부품 품번 구성
const searchPartFirst = ref("1");
const searchPartTwo = ref("01");
const searchPartMid = ref("M");
const searchPartDigit = ref("1");
const searchPartLast = ref("S");

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

const loadProducts = async () => {
  const res = await api.get("/products/");
  products.value = res.data.map((item) => ({
    ...item,
    code: item.new_code || item.code || "",
    old_code: item.old_code || ""
  }));
};

// =====================
// 입고
// =====================
const addStock = async () => {
  if (!quantity.value) return;

  let productCode = code.value.trim();
  const nameValue = nameInput.value.trim();

  if (!productCode && nameValue) {
    const matches = products.value.filter(
      (p) => (p.name || "").trim().toLowerCase() === nameValue.toLowerCase()
    );

    if (matches.length === 0) {
      alert("제품명을 찾을 수 없습니다.");
      return;
    }
    if (matches.length > 1) {
      alert("동일한 제품명이 여러 개입니다. 품번으로 입력해주세요.");
      return;
    }

    productCode = matches[0].code;
  }

  if (!productCode) {
    alert("품번 또는 제품명을 입력하세요.");
    return;
  }

  try {
    await api.post("/inventory/", {
      product_code: productCode,
      quantity: Number(quantity.value)
    });
  } catch (err) {
    const message =
      err?.response?.data?.detail || "입고 실패: 로그인 상태를 확인하세요.";
    alert(message);
    return;
  }

  code.value = "";
  nameInput.value = "";
  quantity.value = "";

  await loadInventory();
  alert("입고 완료");
};

// =====================
// 재고 수정/삭제
// =====================
const startEdit = (item) => {
  editingCode.value = item.code;
  editName.value = item.name || "";
  editLocation.value = item.location || "";
  editMinStock.value = String(item.min_stock ?? "");
  editQuantity.value = String(item.quantity ?? "");
  editReason.value = "";
};

const cancelEdit = () => {
  editingCode.value = "";
  editName.value = "";
  editLocation.value = "";
  editMinStock.value = "";
  editQuantity.value = "";
  editReason.value = "";
};

const saveEdit = async () => {
  if (!editingCode.value) return;

  await api.put(`/products/${editingCode.value}`, {
    name: editName.value,
    location: editLocation.value,
    min_stock: Number(editMinStock.value || 0)
  });

  await api.put(`/inventory/${editingCode.value}`, {
    quantity: Number(editQuantity.value || 0),
    reason: editReason.value
  });

  cancelEdit();
  loadInventory();
};

const deleteInventoryItem = async (productCode) => {
  const ok = window.confirm(`${productCode} 재고 항목을 삭제할까요?`);
  if (!ok) return;

  await api.delete(`/inventory/${productCode}`);
  if (selectedProduct.value === productCode) {
    selectedProduct.value = "";
    productLogs.value = [];
  }
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
  const nameKeyword = (searchNameInput.value || "").trim().toLowerCase();
  const base = inventory.value.filter((item) => item.type === "PART");
  if (!keyword && !nameKeyword) return [];
  return base.filter((item) =>
    (keyword && (item.code || "").toLowerCase().includes(keyword)) ||
    (nameKeyword && (item.name || "").toLowerCase().includes(nameKeyword))
  );
});

// =====================
// 재고 현황 PDF/엑셀
// =====================
const inventoryReportRows = computed(() => {
  return inventory.value
    .map((inv) => ({
      code: inv.code || inv.product_code || "",
      name: inv.name || "",
      quantity: Number(inv.quantity || 0)
    }))
    .sort((a, b) => a.code.localeCompare(b.code));
});

const buildTimestampTag = () => {
  const date = new Date();
  const pad = (v) => String(v).padStart(2, "0");
  return `${date.getFullYear()}${pad(date.getMonth() + 1)}${pad(
    date.getDate()
  )}_${pad(date.getHours())}${pad(date.getMinutes())}`;
};

const saveInventoryPdf = () => {
  const doc = new jsPDF({ orientation: "portrait", unit: "mm", format: "a4" });
  const timestamp = new Date().toLocaleString("ko-KR");
  doc.setFontSize(14);
  doc.text("재고 현황", 14, 16);
  doc.setFontSize(10);
  doc.text(`생성일시: ${timestamp}`, 14, 22);

  const body = inventoryReportRows.value.map((r, i) => [
    String(i + 1),
    r.code,
    r.name || "-",
    String(r.quantity)
  ]);

  autoTable(doc, {
    startY: 26,
    head: [["No", "품번", "제품명", "재고"]],
    body,
    styles: { fontSize: 9 },
    headStyles: { fillColor: [240, 240, 240], textColor: 20 },
    columnStyles: { 3: { halign: "right" } }
  });

  const filename = `inventory_${buildTimestampTag()}.pdf`;
  doc.save(filename);
};

const exportInventoryExcel = () => {
  const rows = inventoryReportRows.value.map((r, i) => ({
    No: i + 1,
    품번: r.code,
    제품명: r.name || "-",
    재고: r.quantity
  }));

  const ws = XLSX.utils.json_to_sheet(rows);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "재고현황");

  const filename = `inventory_${buildTimestampTag()}.xlsx`;
  XLSX.writeFile(wb, filename);
};

onMounted(() => {
  loadInventory();
  loadProducts();
});

const partCode = computed(
  () => `${partFirst.value}${partTwo.value}${partMid.value}${partDigit.value}-${partLast.value}`
);

watch([partFirst, partTwo, partMid, partDigit, partLast], () => {
  code.value = partCode.value;
});

const searchPartCode = computed(
  () =>
    `${searchPartFirst.value}${searchPartTwo.value}${searchPartMid.value}${searchPartDigit.value}-${searchPartLast.value}`
);

watch(
  [searchPartFirst, searchPartTwo, searchPartMid, searchPartDigit, searchPartLast],
  () => {
    searchCode.value = searchPartCode.value;
  }
);

const filteredNameSuggestions = computed(() => {
  const keyword = (searchNameInput.value || "").trim().toLowerCase();
  if (!keyword) return [];
  const base = inventory.value.filter((item) => item.type === "PART");
  return base.filter((item) =>
    (item.name || "").toLowerCase().includes(keyword)
  ).slice(0, 10);
});

const selectNameSuggestion = (name) => {
  searchNameInput.value = name;
  showNameDropdown.value = false;
};

const filteredAddNameSuggestions = computed(() => {
  const keyword = (nameInput.value || "").trim().toLowerCase();
  if (!keyword) return [];
  return products.value
    .filter((p) => p.type === "PART")
    .filter((p) => (p.name || "").toLowerCase().includes(keyword))
    .slice(0, 10);
});

const selectAddNameSuggestion = (name) => {
  nameInput.value = name;
  showAddNameDropdown.value = false;
};

const filteredAddCodeSuggestions = computed(() => {
  const keyword = (code.value || "").trim().toLowerCase();
  if (!keyword) return [];
  return products.value
    .filter((p) => p.type === "PART")
    .filter((p) => (p.code || "").toLowerCase().includes(keyword))
    .slice(0, 10);
});

const selectAddCodeSuggestion = (codeValue) => {
  code.value = codeValue;
  showAddCodeDropdown.value = false;
};
</script>

<template>
  <div>

    <div class="flex items-center justify-between mb-6">
      <h2 class="page-title">📦 재고 관리</h2>
      <div class="flex gap-2">
        <button
          @click="saveInventoryPdf"
          class="btn btn-info"
        >
          재고 PDF 저장
        </button>
        <button
          @click="exportInventoryExcel"
          class="btn btn-success"
        >
          재고 엑셀 저장
        </button>
      </div>
    </div>

    <!-- 입고 -->
    <div class="panel mb-4">
      <div class="panel-header">입고</div>
      <div class="p-3 flex gap-2 items-center flex-wrap">

      <div class="relative w-40">
        <input
          v-model="code"
          @focus="showAddCodeDropdown = true"
          @blur="setTimeout(() => showAddCodeDropdown = false, 200)"
          placeholder="품번 직접 입력"
          class="input w-full"
        />
        <div
          v-if="showAddCodeDropdown && filteredAddCodeSuggestions.length"
          class="absolute bg-white border w-full z-10 max-h-40 overflow-y-auto rounded-lg shadow"
        >
          <div
            v-for="item in filteredAddCodeSuggestions"
            :key="`add-code-${item.code}`"
            @click="selectAddCodeSuggestion(item.code)"
            class="p-2 hover:bg-slate-100 cursor-pointer text-sm"
          >
            {{ item.code }} ({{ item.name }})
          </div>
        </div>
      </div>

      <div class="relative w-48">
        <input
          v-model="nameInput"
          @focus="showAddNameDropdown = true"
          @blur="setTimeout(() => showAddNameDropdown = false, 200)"
          placeholder="제품명"
          class="input w-full"
        />
        <div
          v-if="showAddNameDropdown && filteredAddNameSuggestions.length"
          class="absolute bg-white border w-full z-10 max-h-40 overflow-y-auto rounded-lg shadow"
        >
          <div
            v-for="item in filteredAddNameSuggestions"
            :key="`add-name-${item.code}`"
            @click="selectAddNameSuggestion(item.name)"
            class="p-2 hover:bg-slate-100 cursor-pointer text-sm"
          >
            {{ item.name }} ({{ item.code }})
          </div>
        </div>
      </div>

      <div class="flex items-center gap-1">
        <select v-model="partFirst" class="input w-16">
          <option v-for="n in [1,2,3,4,5]" :key="n" :value="String(n)">
            {{ n }}
          </option>
        </select>
        <select v-model="partTwo" class="input w-20">
          <option v-for="n in 21" :key="n" :value="String(n).padStart(2, '0')">
            {{ String(n).padStart(2, '0') }}
          </option>
        </select>
        <select v-model="partMid" class="input w-16">
          <option value="M">M</option>
          <option value="S">S</option>
        </select>
        <select v-model="partDigit" class="input w-16">
          <option v-for="n in 10" :key="n" :value="String(n - 1)">
            {{ n - 1 }}
          </option>
        </select>
        <select v-model="partLast" class="input w-16">
          <option value="S">S</option>
          <option value="E">E</option>
          <option value="T">T</option>
          <option value="K">K</option>
        </select>
      </div>

      <input v-model="quantity"
        type="number"
        placeholder="수량"
        class="input w-24" />

      <button @click="addStock"
        class="btn btn-primary">
        입고
      </button>

      </div>
    </div>

    <!-- 검색 -->
    <div class="panel mb-6">
      <div class="panel-header">부품 검색</div>
      <div class="p-3 flex gap-2 items-center flex-wrap">

      <div class="flex items-center gap-1">
        <select v-model="searchPartFirst" class="input w-16">
          <option v-for="n in [1,2,3,4,5]" :key="n" :value="String(n)">
            {{ n }}
          </option>
        </select>
        <select v-model="searchPartTwo" class="input w-20">
          <option v-for="n in 21" :key="n" :value="String(n).padStart(2, '0')">
            {{ String(n).padStart(2, '0') }}
          </option>
        </select>
        <select v-model="searchPartMid" class="input w-16">
          <option value="M">M</option>
          <option value="S">S</option>
        </select>
        <select v-model="searchPartDigit" class="input w-16">
          <option v-for="n in 10" :key="n" :value="String(n - 1)">
            {{ n - 1 }}
          </option>
        </select>
        <select v-model="searchPartLast" class="input w-16">
          <option value="S">S</option>
          <option value="E">E</option>
          <option value="T">T</option>
          <option value="K">K</option>
        </select>
      </div>

      <input v-model="searchCode"
        placeholder="품번 검색"
        class="input w-48" />

      <div class="relative w-56">
        <input
          v-model="searchNameInput"
          @focus="showNameDropdown = true"
          @blur="setTimeout(() => showNameDropdown = false, 200)"
          placeholder="제품명 검색"
          class="input w-full"
        />
        <div
          v-if="showNameDropdown && filteredNameSuggestions.length"
          class="absolute bg-white border w-full z-10 max-h-40 overflow-y-auto rounded-lg shadow"
        >
          <div
            v-for="item in filteredNameSuggestions"
            :key="`name-${item.code}`"
            @click="selectNameSuggestion(item.name)"
            class="p-2 hover:bg-slate-100 cursor-pointer text-sm"
          >
            {{ item.name }} ({{ item.code }})
          </div>
        </div>
      </div>

      </div>
    </div>

    <!-- 수정 -->
    <div v-if="editingCode" class="panel p-3 mb-6">
      <div class="font-semibold mb-2">재고 정보 수정: {{ editingCode }}</div>
      <div class="flex flex-wrap gap-2 items-center">
        <input v-model="editName" placeholder="제품명"
          class="input w-40" />
        <input v-model="editLocation" placeholder="위치"
          class="input w-32" />
        <input v-model="editMinStock" type="number" placeholder="최소재고"
          class="input w-24" />
        <input v-model="editQuantity" type="number" placeholder="재고"
          class="input w-24" />

        <input v-model="editReason" placeholder="수량 변경 사유"
          class="input w-64" />

        <button @click="saveEdit" class="btn btn-primary">
          저장
        </button>
        <button @click="cancelEdit" class="btn btn-secondary">
          취소
        </button>
      </div>
    </div>

    <!-- 재고 부족 -->
    <div
      v-if="lowStockItems.length"
      class="mb-4 p-3 bg-rose-50 text-rose-700 rounded-xl border border-rose-100"
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
    <div class="panel overflow-hidden">
      <table class="w-full text-left">

        <thead class="table-head">
          <tr>
            <th class="p-3">제품</th>
            <th class="p-3">위치</th>
            <th class="p-3">현재 재고</th>
            <th class="p-3">최소 재고</th>
            <th class="p-3">관리</th>
          </tr>
        </thead>

        <tbody>
          <tr
            v-for="item in filteredInventory"
            :key="item.code"
            class="border-t hover:bg-slate-50"
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

            <td class="p-3">
              <div class="flex gap-2">
                <button @click="startEdit(item)"
                  class="btn btn-info h-7 px-2 text-xs">
                  수정
                </button>
                <button @click="deleteInventoryItem(item.code)"
                  class="btn btn-danger h-7 px-2 text-xs">
                  삭제
                </button>
              </div>
            </td>

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

      <div class="panel overflow-hidden">
        <table class="w-full text-left">

          <thead class="table-head">
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
