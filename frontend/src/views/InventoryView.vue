<script setup>
import { ref, onMounted, computed, watch } from "vue";
import api from "../api";
import * as XLSX from "xlsx";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";

const inventory = ref([]);
const products = ref([]);
const companies = ref([]);
const searchCode = ref("");
const searchNameInput = ref("");
const showNameDropdown = ref(false);
const typeFilter = ref("PART");
const showAllPartsModal = ref(false);

const code = ref("");
const nameInput = ref("");
const quantity = ref("");
const showAddNameDropdown = ref(false);
const showAddCodeDropdown = ref(false);
const oldCodeInput = ref("");
const materialInput = ref("");
const specInput = ref("");
const supplierCompanyId = ref("");
const supplierInput = ref("");
const showSupplierDropdown = ref(false);
const minStockInput = ref("");
const locationInput = ref("");
const uploadFile = ref(null);
const uploadInputRef = ref(null);

// 수정
const editingCode = ref("");
const editName = ref("");
const editOldCode = ref("");
const editMaterial = ref("");
const editSpec = ref("");
const editLocation = ref("");
const editMinStock = ref("");
const editQuantity = ref("");
const editReason = ref("");
const editSupplierCompanyId = ref("");

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
  inventory.value = res.data.map((item) => ({
    ...item,
    new_code: item.new_code || item.code || "",
    old_code: item.old_code || "",
    name: item.name || "",
    material: item.material || "",
    spec: item.spec || "",
    location: item.location || "",
    type: (item.type || "PART").toString().toUpperCase()
  }));
};

const loadProducts = async () => {
  const res = await api.get("/products/");
  products.value = res.data.map((item) => ({
    ...item,
    code: item.new_code || item.code || "",
    old_code: item.old_code || ""
  }));
};

const loadCompanies = async () => {
  const res = await api.get("/companies/");
  companies.value = res.data;
};

// =====================
// 입고
// =====================
const addStock = async () => {
  if (!code.value && !nameInput.value) return;
  if (!quantity.value) return;

  let productCode = code.value.trim();
  const nameValue = nameInput.value.trim();
  const supplierValue = supplierInput.value.trim();
  const locationValue = locationInput.value.trim();
  const minStockValue = Number(minStockInput.value || 0);
  let supplierId = supplierCompanyId.value ? Number(supplierCompanyId.value) : null;

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

  if (!supplierId && supplierValue) {
    const match = companies.value.find(
      (c) => (c.name || "").trim().toLowerCase() === supplierValue.toLowerCase()
    );
    if (match) {
      supplierId = match.id;
    } else {
      const created = await api.post("/companies/", {
        name: supplierValue,
        phone: "",
        fax: "",
        address: ""
      });
      supplierId = created?.data?.id || null;
      await loadCompanies();
    }
  }

  try {
    // 단품 등록 (신품번 기준)
    await api.post("/products/", {
      code: productCode,
      old_code: oldCodeInput.value.trim(),
      name: nameValue,
      type: "PART",
      material: materialInput.value.trim(),
      spec: specInput.value.trim(),
      quantity: Number(quantity.value),
      min_stock: minStockValue,
      location: locationValue,
      supplier_company_id: supplierId
    });
  } catch (err) {
    const message =
      err?.response?.data?.detail || "등록 실패: 로그인 상태를 확인하세요.";
    alert(message);
    return;
  }

  code.value = "";
  oldCodeInput.value = "";
  nameInput.value = "";
  materialInput.value = "";
  specInput.value = "";
  supplierCompanyId.value = "";
  supplierInput.value = "";
  minStockInput.value = "";
  locationInput.value = "";
  quantity.value = "";

  await loadInventory();
  await loadProducts();
  alert("입고 완료");
};

// =====================
// 재고 수정/삭제
// =====================
const startEdit = (item) => {
  editingCode.value = item.new_code || item.code || "";
  editName.value = item.name || "";
  editOldCode.value = item.old_code || "";
  editMaterial.value = item.material || "";
  editSpec.value = item.spec || "";
  editLocation.value = item.location || "";
  editMinStock.value = String(item.min_stock ?? "");
  editQuantity.value = String(item.quantity ?? "");
  editSupplierCompanyId.value = item.supplier_company_id
    ? String(item.supplier_company_id)
    : "";
  editReason.value = "";
};

const cancelEdit = () => {
  editingCode.value = "";
  editName.value = "";
  editOldCode.value = "";
  editMaterial.value = "";
  editSpec.value = "";
  editLocation.value = "";
  editMinStock.value = "";
  editQuantity.value = "";
  editSupplierCompanyId.value = "";
  editReason.value = "";
};

const saveEdit = async () => {
  if (!editingCode.value) return;

  await api.put(`/products/${editingCode.value}`, {
    old_code: editOldCode.value,
    name: editName.value,
    material: editMaterial.value,
    spec: editSpec.value,
    location: editLocation.value,
    min_stock: Number(editMinStock.value || 0),
    supplier_company_id: editSupplierCompanyId.value
      ? Number(editSupplierCompanyId.value)
      : null
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
  const base = inventory.value.filter(
    (item) => (item.type || "PART").toString().toUpperCase() === "PART"
  );
  if (!keyword && !nameKeyword) return [];
  return base.filter((item) => {
    const codeValue = (item.new_code || item.code || "")
      .toString()
      .toLowerCase();
    const oldValue = (item.old_code || "").toString().toLowerCase();
    const nameValue = (item.name || "").toString().toLowerCase();
    return (
      (keyword && (codeValue.includes(keyword) || oldValue.includes(keyword))) ||
      (nameKeyword && nameValue.includes(nameKeyword))
    );
  });
});

const allPartsSorted = computed(() => {
  return inventory.value
    .filter(
      (item) => (item.type || "PART").toString().toUpperCase() === "PART"
    )
    .slice()
    .sort((a, b) =>
      String(a.new_code || a.code || "").localeCompare(
        String(b.new_code || b.code || "")
      )
    );
});

// =====================
// 재고 현황 PDF/엑셀
// =====================
const inventoryReportRows = computed(() => {
  return inventory.value
    .map((inv) => ({
      code: inv.new_code || inv.code || inv.product_code || "",
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
  const rows = inventory.value
    .filter(
      (item) => (item.type || "PART").toString().toUpperCase() === "PART"
    )
    .map((item) => ({
      기존품번: item.old_code || "",
      신품번: item.new_code || item.code || "",
      품명: item.name || "",
      규격: item.spec || "",
      재질: item.material || "",
      재고수량: Number(item.quantity || 0),
      최소재고: Number(item.min_stock || 0),
      보관위치: item.location || "",
      발주처: getCompanyName(item.supplier_company_id)
    }));

  const ws = XLSX.utils.json_to_sheet(rows);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "단품목록");

  const filename = `parts_${buildTimestampTag()}.xlsx`;
  XLSX.writeFile(wb, filename);
};

onMounted(() => {
  loadInventory();
  loadProducts();
  loadCompanies();
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
  const base = inventory.value.filter(
    (item) => (item.type || "PART").toString().toUpperCase() === "PART"
  );
  return base
    .filter((item) => (item.name || "").toLowerCase().includes(keyword))
    .slice(0, 10);
});

const selectNameSuggestion = (name) => {
  searchNameInput.value = name;
  showNameDropdown.value = false;
};

const getCompanyName = (companyId) => {
  if (!companyId) return "-";
  const company = companies.value.find((c) => c.id === companyId);
  return company?.name || "-";
};

const deferHide = (fn) => {
  window.setTimeout(fn, 200);
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
    .filter((p) =>
      (p.code || "").toLowerCase().includes(keyword) ||
      (p.old_code || "").toLowerCase().includes(keyword)
    )
    .slice(0, 10);
});

const filteredSupplierSuggestions = computed(() => {
  const keyword = (supplierInput.value || "").trim().toLowerCase();
  if (!keyword) return [];
  return companies.value
    .filter((c) => (c.name || "").toLowerCase().includes(keyword))
    .slice(0, 10);
});

const selectSupplierSuggestion = (company) => {
  supplierInput.value = company.name;
  supplierCompanyId.value = String(company.id);
  showSupplierDropdown.value = false;
};

const selectAddCodeSuggestion = (codeValue) => {
  code.value = codeValue;
  showAddCodeDropdown.value = false;
};

const filteredSearchCodeSuggestions = computed(() => {
  const keyword = (searchCode.value || "").trim().toLowerCase();
  if (!keyword) return [];
  return inventory.value
    .filter(
      (item) => (item.type || "PART").toString().toUpperCase() === "PART"
    )
    .filter((item) =>
      (item.new_code || item.code || "")
        .toString()
        .toLowerCase()
        .includes(keyword) ||
      (item.old_code || "").toString().toLowerCase().includes(keyword)
    )
    .slice(0, 10);
});

const selectSearchCodeSuggestion = (codeValue) => {
  searchCode.value = codeValue;
};

const onFileChange = (e) => {
  uploadFile.value = e.target.files?.[0] || null;
};

const uploadPartsExcel = async () => {
  if (!uploadFile.value) return;
  const form = new FormData();
  form.append("file", uploadFile.value);
  const res = await api.post("/products/import-parts", form, {
    headers: { "Content-Type": "multipart/form-data" }
  });
  uploadFile.value = null;
  if (uploadInputRef.value) {
    uploadInputRef.value.value = "";
  }
  await loadInventory();
  await loadProducts();
  const created = Number(res?.data?.created || 0);
  const updated = Number(res?.data?.updated || 0);
  const skipped = Number(res?.data?.skipped || 0);
  const rowsTotal = Number(res?.data?.rows_total || 0);
  if (created + updated === 0) {
    alert(
      `업로드 완료(처리 0건, 스킵 ${skipped}건, 총행 ${rowsTotal}건) — 업로드 파일 저장 여부/시트/헤더를 확인해줘. (콘솔에 상세 로그 출력됨)`
    );
    return;
  }
  alert(
    `엑셀 업로드 완료 (신규 ${created}건, 업데이트 ${updated}건, 스킵 ${skipped}건, 총행 ${rowsTotal}건)`
  );
};
</script>

<template>
  <div>

    <div class="flex items-center justify-between mb-6">
      <h2 class="page-title">📦 단품 관리</h2>
      <div class="flex gap-2 items-center">
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
      <div class="panel-header">단품 등록</div>
      <div class="p-3 flex flex-col gap-2">

      <div class="flex gap-2 items-center flex-wrap">
        <input v-model="oldCodeInput"
          placeholder="구품번"
          class="input w-32" />

        <div class="relative w-40">
          <input
            v-model="code"
            @focus="showAddCodeDropdown = true"
            @blur="deferHide(() => showAddCodeDropdown = false)"
            placeholder="신품번"
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

        <div class="relative w-56">
          <input
            v-model="nameInput"
            @focus="showAddNameDropdown = true"
            @blur="deferHide(() => showAddNameDropdown = false)"
            placeholder="품명"
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

        <input v-model="quantity"
          type="number"
          placeholder="재고수량"
          class="input w-24" />

        <button @click="addStock"
          class="btn btn-primary">
          등록
        </button>
      </div>

      <div class="flex gap-2 items-center flex-wrap">
        <input v-model="materialInput"
          placeholder="재질"
          class="input w-32" />

        <input v-model="specInput"
          placeholder="규격"
          class="input w-32" />

        <input v-model="minStockInput"
          type="number"
          placeholder="최소재고"
          class="input w-24" />

        <input v-model="locationInput"
          placeholder="보관위치"
          class="input w-28" />

        <div class="relative w-48">
          <input
            v-model="supplierInput"
            @focus="showSupplierDropdown = true"
            @blur="deferHide(() => showSupplierDropdown = false)"
            placeholder="발주처"
            class="input w-full"
          />
          <div
            v-if="showSupplierDropdown && filteredSupplierSuggestions.length"
            class="absolute bg-white border w-full z-10 max-h-40 overflow-y-auto rounded-lg shadow"
          >
            <div
              v-for="c in filteredSupplierSuggestions"
              :key="`supplier-${c.id}`"
              @click="selectSupplierSuggestion(c)"
              class="p-2 hover:bg-slate-100 cursor-pointer text-sm"
            >
              {{ c.name }}
            </div>
          </div>
        </div>
      </div>
    </div>
    </div>

    <div class="panel mb-4">
      <div class="panel-header">엑셀 업로드</div>
      <div class="p-3 flex gap-2 items-center flex-wrap">
        <input ref="uploadInputRef" type="file" @change="onFileChange" class="input w-72" />
        <button @click="uploadPartsExcel" class="btn btn-primary">업로드</button>
      </div>
    </div>

    <!-- 검색 -->
    <div class="panel mb-6">
      <div class="panel-header">부품 검색</div>
      <div class="p-3 flex gap-2 items-center flex-wrap">

      <div class="relative w-48">
        <input v-model="searchCode"
          placeholder="구/신품번 검색"
          class="input w-full" />
        <div
          v-if="filteredSearchCodeSuggestions.length"
          class="absolute bg-white border w-full z-10 max-h-40 overflow-y-auto rounded-lg shadow"
        >
          <div
            v-for="item in filteredSearchCodeSuggestions"
            :key="`search-code-${item.new_code || item.code}`"
            @click="selectSearchCodeSuggestion(item.new_code || item.code)"
            class="p-2 hover:bg-slate-100 cursor-pointer text-sm"
          >
            {{ item.new_code || item.code }} / {{ item.old_code || "-" }} ({{ item.name }})
          </div>
        </div>
      </div>

      <div class="relative w-56">
        <input
          v-model="searchNameInput"
          @focus="showNameDropdown = true"
          @blur="deferHide(() => showNameDropdown = false)"
          placeholder="품명 검색"
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

      <button
        class="btn btn-secondary"
        @click="showAllPartsModal = true"
      >
        전체 단품 목록
      </button>

      </div>
    </div>

    <!-- 전체 단품 모달 -->
    <div v-if="showAllPartsModal" class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-black/40" @click="showAllPartsModal = false"></div>
      <div class="relative bg-white w-[90vw] max-w-5xl max-h-[80vh] rounded-2xl shadow-xl overflow-hidden">
        <div class="flex items-center justify-between px-4 py-3 border-b">
          <div class="font-semibold">전체 단품 목록 ({{ allPartsSorted.length }})</div>
          <button class="btn btn-secondary" @click="showAllPartsModal = false">닫기</button>
        </div>
        <div class="p-3 overflow-auto max-h-[70vh]">
          <table class="w-full text-left">
            <thead class="table-head">
              <tr>
                <th class="p-2">구품번</th>
                <th class="p-2">신품번</th>
                <th class="p-2">품명</th>
                <th class="p-2">재질</th>
                <th class="p-2">규격</th>
                <th class="p-2">재고</th>
                <th class="p-2">최소재고</th>
                <th class="p-2">보관위치</th>
                <th class="p-2">발주처</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in allPartsSorted" :key="`modal-${item.new_code || item.code}`" class="border-t hover:bg-slate-50">
                <td class="p-2 font-medium">{{ item.old_code || "-" }}</td>
                <td class="p-2">{{ item.new_code || "-" }}</td>
                <td class="p-2">{{ item.name || "-" }}</td>
                <td class="p-2">{{ item.material || "-" }}</td>
                <td class="p-2">{{ item.spec || "-" }}</td>
                <td class="p-2">{{ item.quantity }}</td>
                <td class="p-2">{{ item.min_stock }}</td>
                <td class="p-2">{{ item.location || "-" }}</td>
                <td class="p-2">{{ getCompanyName(item.supplier_company_id) }}</td>
              </tr>
              <tr v-if="allPartsSorted.length === 0">
                <td colspan="9" class="p-4 text-center text-gray-400">목록이 없습니다.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- 수정 -->
    <div v-if="editingCode" class="panel p-3 mb-6">
      <div class="font-semibold mb-2">재고 정보 수정: {{ editingCode }}</div>
      <div class="flex flex-wrap gap-2 items-center">
        <input v-model="editOldCode" placeholder="구품번"
          class="input w-32" />
        <input v-model="editName" placeholder="제품명"
          class="input w-40" />
        <input v-model="editMaterial" placeholder="재질"
          class="input w-28" />
        <input v-model="editSpec" placeholder="규격"
          class="input w-28" />
        <input v-model="editLocation" placeholder="위치"
          class="input w-32" />
        <select v-model="editSupplierCompanyId" class="input w-40">
          <option value="">발주처 선택</option>
          <option v-for="c in companies" :key="c.id" :value="String(c.id)">
            {{ c.name }}
          </option>
        </select>
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
          :key="`low-${item.new_code || item.code}`"
        >
          - {{ item.name || "이름없음" }} ({{ item.new_code || item.code }}) :
          {{ item.min_stock - item.quantity }}개 부족
        </div>
      </div>
    </div>

    <!-- 재고 테이블 -->
    <div class="panel overflow-hidden">
      <table class="w-full text-left">

        <thead class="table-head">
          <tr>
            <th class="p-3">구품번</th>
            <th class="p-3">신품번</th>
            <th class="p-3">품명</th>
            <th class="p-3">재질</th>
            <th class="p-3">규격</th>
            <th class="p-3">현재 재고</th>
            <th class="p-3">최소 재고</th>
            <th class="p-3">보관위치</th>
            <th class="p-3">발주처</th>
            <th class="p-3">관리</th>
          </tr>
        </thead>

        <tbody>
          <tr
            v-for="item in filteredInventory"
            :key="item.new_code || item.code"
            class="border-t hover:bg-slate-50"
          >

            <!-- ⭐ 클릭은 여기(td)에 걸어야 함 -->
            <td class="p-3 cursor-pointer"
                @click="loadProductLogs(item.new_code || item.code)">
              <div class="font-semibold">{{ item.old_code || "-" }}</div>
            </td>

            <td class="p-3">{{ item.new_code || "-" }}</td>

            <td class="p-3">{{ item.name || "-" }}</td>

            <td class="p-3">{{ item.material || "-" }}</td>

            <td class="p-3">{{ item.spec || "-" }}</td>

            <td class="p-3 font-bold"
                :class="item.quantity < item.min_stock ? 'text-red-500' : 'text-blue-600'">
              {{ item.quantity }}
            </td>

            <td class="p-3">{{ item.min_stock }}</td>

            <td class="p-3">{{ item.location || "-" }}</td>

            <td class="p-3">{{ getCompanyName(item.supplier_company_id) }}</td>

            <td class="p-3">
              <div class="flex gap-2">
                <button @click="startEdit(item)"
                  class="btn btn-info h-7 px-2 text-xs">
                  수정
                </button>
                <button @click="deleteInventoryItem(item.new_code || item.code)"
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
