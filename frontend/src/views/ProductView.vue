<script setup>
import { ref, onMounted, onUnmounted, computed } from "vue";
import api from "../api";

const products = ref([]);
const boms = ref([]);
const companies = ref([]);

// 제품 입력
const code = ref("");
const oldCodeInput = ref("");
const name = ref("");
const materialInput = ref("");
const specInput = ref("");
const type = ref("FINISHED");

// 납품처 선택
const supplierCompanyId = ref("");
const supplierInput = ref("");
const showSupplierDropdown = ref(false);

// BOM 입력 상태
const bomInput = ref({});
const searchInput = ref({});
const showDropdown = ref({});
const expandedBOM = ref({});
const productSearch = ref("");
const productSearchInput = ref("");
const listMode = ref("FINISHED");
const showNameDropdown = ref(false);

// 등록 입력 추천
const showCreateCodeDropdown = ref(false);
const showCreateNameDropdown = ref(false);
const finishedUploadFile = ref(null);
const showBomModal = ref(false);
const bomParentInput = ref("");
const bomParentCode = ref("");
const bomRows = ref([]);
const bomQuickSearch = ref("");
const showBomParentDropdown = ref(false);
const showBomPartDropdown = ref({});
const bomEditState = ref({});

// =====================
// 데이터 로드
// =====================
const loadData = async () => {
  const p = await api.get("/products/");
  const b = await api.get("/bom/");
  const c = await api.get("/companies/");

  products.value = p.data.map((item) => ({
    ...item,
    code: item.new_code || item.code || "",
    old_code: item.old_code || ""
  }));
  boms.value = b.data;
  companies.value = c.data;
};

const closeAllDropdowns = () => {
  showSupplierDropdown.value = false;
  showNameDropdown.value = false;
  showCreateCodeDropdown.value = false;
  showCreateNameDropdown.value = false;
  showBomParentDropdown.value = false;
  showBomPartDropdown.value = {};
  showDropdown.value = {};
};

// =====================
// 제품 등록
// =====================
const createProduct = async () => {
  const codeValue = (code.value || "").trim();
  const nameValue = (name.value || "").trim();
  if (!codeValue) return alert("품번 입력");

  try {
    await api.post("/products/", {
      code: codeValue,
      name: nameValue,
      type: type.value,
      location: "",
      min_stock: 0,
      old_code: oldCodeInput.value.trim(),
      material: "",
      spec: specInput.value.trim(),
      supplier_company_id: null
    });
  } catch (err) {
    const message =
      err?.response?.data?.detail || "등록 실패: 품번 중복 여부를 확인하세요.";
    if (message.includes("이미 존재")) {
      const existing = products.value.find(
        (p) => (p.code || "").trim() === codeValue
      );
      if (existing && existing.type !== type.value) {
        const ok = window.confirm(
          `이미 ${existing.type === "PART" ? "부품" : "완제품"}으로 등록되어 있습니다. ` +
          `이 품번을 ${type.value === "FINISHED" ? "완제품" : "부품"}으로 변경할까요?`
        );
        if (ok) {
          await api.put(`/products/${codeValue}`, {
            name: nameValue || existing.name,
            type: type.value,
            old_code: oldCodeInput.value.trim() || existing.old_code || "",
            material: "",
            spec: specInput.value.trim() || existing.spec || "",
            location: "",
            min_stock: 0,
            supplier_company_id: null
          });
          loadData();
          return;
        }
      }
    }
    alert(message);
    return;
  }

  code.value = "";
  oldCodeInput.value = "";
  name.value = "";
  specInput.value = "";
  supplierCompanyId.value = "";
  supplierInput.value = "";

  loadData();
};

const deleteProduct = async (code) => {
  const ok = window.confirm(`${code} 제품을 삭제할까요? 관련 BOM/재고/별칭도 함께 삭제됩니다.`);
  if (!ok) return;

  await api.delete(`/products/${code}`);
  loadData();
};

// =====================
// BOM 필터
// =====================
const getBOM = (code) => {
  return boms.value.filter(b => b.parent_code === code);
};

// =====================
// BOM 추가
// =====================
const addBOM = async (parent_code) => {
  const input = bomInput.value[parent_code];

  if (!input || !input.child || !input.qty) return;

  await api.post("/bom/", {
    parent_code: parent_code,
    child_code: input.child,
    quantity: Number(input.qty)
  });

  bomInput.value[parent_code] = { child: "", qty: "" };
  searchInput.value[parent_code] = "";

  loadData();
};

// =====================
// BOM 삭제
// =====================
const deleteBOM = async (id) => {
  await api.delete(`/bom/${id}`);
  loadData();
};

const startBomEdit = (bom) => {
  const part = getProductByCode(bom.child_code);
  bomEditState.value[bom.id] = {
    partCode: bom.child_code,
    partInput: part
      ? `${part.name} (${part.code}${part.old_code ? ` / ${part.old_code}` : ""})`
      : bom.child_code,
    qty: String(bom.quantity ?? ""),
  };
};

const cancelBomEdit = (bomId) => {
  delete bomEditState.value[bomId];
  delete showBomPartDropdown.value[`edit-${bomId}`];
};

const filteredBomEditParts = (bomId) => {
  const keyword = (bomEditState.value[bomId]?.partInput || "").trim().toLowerCase();
  return products.value.filter((p) =>
    p.type === "PART" &&
    (
      !keyword ||
      (p.code || "").toLowerCase().includes(keyword) ||
      (p.old_code || "").toLowerCase().includes(keyword) ||
      (p.name || "").toLowerCase().includes(keyword)
    )
  );
};

const selectBomEditPart = (bomId, p) => {
  const current = bomEditState.value[bomId];
  if (!current) return;
  current.partCode = p.code;
  current.partInput = `${p.name} (${p.code}${p.old_code ? ` / ${p.old_code}` : ""})`;
  showBomPartDropdown.value[`edit-${bomId}`] = false;
};

const saveBomEdit = async (bom) => {
  const current = bomEditState.value[bom.id];
  if (!current) return;

  const partCode = current.partCode || resolveBomCode(current.partInput, "PART");
  const quantity = Number(current.qty || 0);
  if (!partCode || quantity <= 0) {
    alert("부품과 수량을 올바르게 입력하세요.");
    return;
  }

  try {
    await api.put(`/bom/${bom.id}`, {
      child_code: partCode,
      quantity,
    });
  } catch (err) {
    alert(err?.response?.data?.detail || "BOM 수정 중 오류가 발생했습니다.");
    return;
  }

  cancelBomEdit(bom.id);
  await loadData();
};

// =====================
// 자동완성 필터
// =====================
const filteredParts = (parent_code) => {
  const keyword = (searchInput.value[parent_code] || "").trim().toLowerCase();

  return products.value.filter(p =>
    p.type === "PART" &&
    (
      !keyword ||
      (p.code || "").toLowerCase().includes(keyword) ||
      (p.old_code || "").toLowerCase().includes(keyword) ||
      (p.name || "").toLowerCase().includes(keyword)
    )
  );
};

// =====================
// 선택
// =====================
const selectPart = (parent_code, code) => {
  (bomInput.value[parent_code] ||= {}).child = code;
  searchInput.value[parent_code] = code;
  showDropdown.value[parent_code] = false;
};

const filteredBomParents = computed(() => {
  const keyword = (bomParentInput.value || "").trim().toLowerCase();
  return products.value.filter(p =>
    p.type === "FINISHED" &&
    (
      !keyword ||
      (p.code || "").toLowerCase().includes(keyword) ||
      (p.old_code || "").toLowerCase().includes(keyword) ||
      (p.name || "").toLowerCase().includes(keyword)
    )
  );
});

const selectBomParent = (p) => {
  bomParentCode.value = p.code;
  bomParentInput.value = `${p.name} (${p.code}${p.old_code ? ` / ${p.old_code}` : ""})`;
  showBomParentDropdown.value = false;
};

const initBomRows = (count = 5) => {
  bomRows.value = Array.from({ length: count }, () => ({
    partInput: "",
    partCode: "",
    qty: ""
  }));
  showBomPartDropdown.value = {};
};

const addBomRow = () => {
  bomRows.value.push({
    partInput: "",
    partCode: "",
    qty: ""
  });
};

const filteredBomParts = (row) => {
  const keyword = (row.partInput || "").trim().toLowerCase();
  return products.value.filter(p =>
    p.type === "PART" &&
    (
      !keyword ||
      (p.code || "").toLowerCase().includes(keyword) ||
      (p.old_code || "").toLowerCase().includes(keyword) ||
      (p.name || "").toLowerCase().includes(keyword)
    )
  );
};

const selectBomPart = (index, p) => {
  const row = bomRows.value[index];
  if (!row) return;
  row.partCode = p.code;
  row.partInput = `${p.name} (${p.code}${p.old_code ? ` / ${p.old_code}` : ""})`;
  showBomPartDropdown.value[index] = false;
};

const filteredBomQuickParts = computed(() => {
  const keyword = (bomQuickSearch.value || "").trim().toLowerCase();
  if (!keyword) return [];
  return products.value.filter(p =>
    p.type === "PART" &&
    (
      (p.code || "").toLowerCase().includes(keyword) ||
      (p.old_code || "").toLowerCase().includes(keyword) ||
      (p.name || "").toLowerCase().includes(keyword)
    )
  );
});

const isBomQuickChecked = (code) => {
  return bomRows.value.some((row) => row.partCode === code);
};

const toggleBomQuickPart = (p) => {
  const exists = isBomQuickChecked(p.code);
  if (exists) {
    bomRows.value = bomRows.value.filter((row) => row.partCode !== p.code);
    return;
  }

  const emptyIndex = bomRows.value.findIndex((row) => !row.partCode && !row.partInput && !row.qty);
  const newRow = {
    partInput: `${p.name} (${p.code}${p.old_code ? ` / ${p.old_code}` : ""})`,
    partCode: p.code,
    qty: ""
  };
  if (emptyIndex >= 0) {
    bomRows.value.splice(emptyIndex, 1, newRow);
  } else {
    bomRows.value.push(newRow);
  }
};

const resetBomModal = () => {
  bomParentInput.value = "";
  bomParentCode.value = "";
  initBomRows();
  bomQuickSearch.value = "";
  showBomParentDropdown.value = false;
};

const openBomModal = () => {
  resetBomModal();
  showBomModal.value = true;
};

const addBomRows = (count) => {
  const n = Number(count);
  if (!Number.isFinite(n) || n <= 0) return;
  for (let i = 0; i < n; i += 1) {
    bomRows.value.push({
      partInput: "",
      partCode: "",
      qty: ""
    });
  }
};

const addBomRowsPrompt = () => {
  const input = window.prompt("몇 줄 추가할까요?", "1");
  if (!input) return;
  addBomRows(Number(input));
};

const resolveBomCode = (raw, type) => {
  const value = (raw || "").trim();
  if (!value) return "";
  const lower = value.toLowerCase();
  const found = products.value.find(p =>
    p.type === type &&
    ((p.code || "").toLowerCase() === lower ||
      (p.old_code || "").toLowerCase() === lower ||
      (p.name || "").toLowerCase() === lower)
  );
  return found ? found.code : value;
};

const saveBomModal = async () => {
  const parentCode = bomParentCode.value || resolveBomCode(bomParentInput.value, "FINISHED");
  if (!parentCode) {
    return alert("완제품을 선택하세요.");
  }

  const payloads = [];
  for (const row of bomRows.value) {
    const partCode = row.partCode || resolveBomCode(row.partInput, "PART");
    const qty = Number(row.qty);
    if (!partCode && !qty) continue;
    if (!partCode || !qty) {
      return alert("부품/수량을 모두 입력하세요.");
    }
    payloads.push({ parent_code: parentCode, child_code: partCode, quantity: qty });
  }

  if (payloads.length === 0) {
    return alert("등록할 BOM 항목이 없습니다.");
  }

  for (const payload of payloads) {
    await api.post("/bom/", payload);
  }

  resetBomModal();
  showBomModal.value = false;
  loadData();
};

const toggleBOM = (code) => {
  expandedBOM.value = {
    ...expandedBOM.value,
    [code]: !expandedBOM.value[code]
  };
};

const getProductByCode = (productCode) => {
  return products.value.find((p) => (p.code || "") === (productCode || "")) || null;
};

const filteredProducts = computed(() => {
  const keyword = (productSearch.value || "").trim().toLowerCase();
  const base = products.value.filter((p) => p.type === "FINISHED");
  const sorted = [...base].sort((a, b) =>
    (a.code || "").localeCompare(b.code || "")
  );
  if (!keyword) return listMode.value === "ALL" ? sorted : [];
  return sorted.filter((p) => {
    const codeMatch = (p.code || "").toLowerCase().includes(keyword);
    const oldCodeMatch = (p.old_code || "").toLowerCase().includes(keyword);
    const nameMatch = (p.name || "").toLowerCase().includes(keyword);
    return codeMatch || oldCodeMatch || nameMatch;
  });
});

const handleGlobalClick = () => closeAllDropdowns();

onMounted(() => {
  loadData();
  window.addEventListener("click", handleGlobalClick);
});

onUnmounted(() => {
  window.removeEventListener("click", handleGlobalClick);
});

const applySearch = () => {
  productSearch.value = productSearchInput.value;
};

const filteredNameSuggestions = computed(() => {
  const keyword = (productSearchInput.value || "").trim().toLowerCase();
  if (!keyword) return [];
  return products.value
    .filter((p) =>
      listMode.value === "ALL" ? true : p.type === "FINISHED"
    )
    .filter((p) =>
      (p.name || "").toLowerCase().includes(keyword) ||
      (p.code || "").toLowerCase().includes(keyword) ||
      (p.old_code || "").toLowerCase().includes(keyword)
    )
    .slice(0, 10);
});

const selectNameSuggestion = (item) => {
  const searchValue = item.code || item.old_code || item.name || "";
  productSearchInput.value = searchValue;
  productSearch.value = searchValue;
  showNameDropdown.value = false;
};

const filteredCreateCodeSuggestions = computed(() => {
  const keyword = (code.value || "").trim().toLowerCase();
  if (!keyword) return [];
  return products.value
    .filter((p) => (p.code || "").toLowerCase().includes(keyword))
    .slice(0, 10);
});

const filteredCreateNameSuggestions = computed(() => {
  const keyword = (name.value || "").trim().toLowerCase();
  if (!keyword) return [];
  return products.value
    .filter((p) => (p.name || "").toLowerCase().includes(keyword))
    .slice(0, 10);
});

const selectCreateCodeSuggestion = (codeValue) => {
  code.value = codeValue;
  showCreateCodeDropdown.value = false;
};

const selectCreateNameSuggestion = (item) => {
  name.value = item?.name || "";
  showCreateNameDropdown.value = false;
};

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

const onFinishedFileChange = (e) => {
  finishedUploadFile.value = e.target.files?.[0] || null;
};

const uploadFinishedExcel = async () => {
  if (!finishedUploadFile.value) return;
  const buildUploadForm = (duplicateAction) => {
    const form = new FormData();
    form.append("file", finishedUploadFile.value);
    form.append("duplicate_action", duplicateAction);
    return form;
  };

  let res;
  try {
    res = await api.post("/products/import-finished", buildUploadForm("prompt"), {
      headers: { "Content-Type": "multipart/form-data" }
    });
  } catch (err) {
    const detail = err?.response?.data?.detail;
    if (err?.response?.status === 409 && detail?.duplicate_count) {
      const previewCodes = Array.isArray(detail.duplicate_codes) && detail.duplicate_codes.length
        ? `\n중복 품번 예시: ${detail.duplicate_codes.join(", ")}`
        : "";
      const overwrite = window.confirm(
        `이미 등록된 완제품 ${detail.duplicate_count}건이 있습니다.${previewCodes}\n\n확인: 기존 완제품 덮어쓰기\n취소: 중복 완제품 스킵`
      );
      const duplicateAction = overwrite ? "overwrite" : "skip";
      res = await api.post("/products/import-finished", buildUploadForm(duplicateAction), {
        headers: { "Content-Type": "multipart/form-data" }
      });
    } else {
      alert(detail?.message || detail || "완제품 엑셀 업로드 중 오류가 발생했습니다.");
      return;
    }
  }

  finishedUploadFile.value = null;
  await loadData();
  const created = Number(res?.data?.created || 0);
  const updated = Number(res?.data?.updated || 0);
  const skipped = Number(res?.data?.skipped || 0);
  const rowsTotal = Number(res?.data?.rows_total || 0);
  const autoGenerated = Number(res?.data?.auto_generated || 0);
  alert(`완제품 엑셀 업로드 완료 (신규 ${created}건, 업데이트 ${updated}건, 스킵 ${skipped}건, 총행 ${rowsTotal}건, 자동부여 ${autoGenerated}건)`);
};

const deferHide = (fn) => {
  window.setTimeout(fn, 200);
};
</script>

<template>
  <div>

    <h2 class="page-title mb-6">📦 완제품 관리</h2>

    <!-- 완제품 등록 -->
    <div class="panel p-3 mb-6">
      <div class="flex gap-2 items-center flex-wrap">
        <input v-model="oldCodeInput"
          placeholder="구품번"
          class="input w-32" />

        <div class="relative w-40" @click.stop>
          <input
            v-model="code"
            @focus="showCreateCodeDropdown = true"
            @blur="deferHide(() => showCreateCodeDropdown = false)"
            placeholder="신품번"
            class="input w-full"
          />
          <div
            v-if="showCreateCodeDropdown && filteredCreateCodeSuggestions.length"
            class="absolute bg-white border w-full z-20 max-h-40 overflow-y-auto shadow rounded-lg"
          >
            <div
              v-for="item in filteredCreateCodeSuggestions"
              :key="`create-code-${item.code}`"
              @click="selectCreateCodeSuggestion(item.code)"
              class="p-2 hover:bg-slate-100 cursor-pointer text-sm"
            >
              {{ item.code }} ({{ item.name }})
            </div>
          </div>
        </div>

        <div class="relative w-56" @click.stop>
          <input
            v-model="name"
            @focus="showCreateNameDropdown = true"
            @blur="deferHide(() => showCreateNameDropdown = false)"
            placeholder="품명"
            class="input w-full"
          />
          <div
            v-if="showCreateNameDropdown && filteredCreateNameSuggestions.length"
            class="absolute bg-white border w-full z-20 max-h-40 overflow-y-auto shadow rounded-lg"
          >
            <div
              v-for="item in filteredCreateNameSuggestions"
              :key="`create-name-${item.code}`"
              @click="selectCreateNameSuggestion(item)"
              class="p-2 hover:bg-slate-100 cursor-pointer text-sm"
            >
              {{ item.name }} ({{ item.code }})
            </div>
          </div>
        </div>

        <input v-model="specInput"
          placeholder="규격"
          class="input w-40" />

        <button @click="createProduct" class="btn btn-primary">
          완제품 등록
        </button>
      </div>
    </div>

    <div class="panel mb-6">
      <div class="panel-header">완제품 엑셀 업로드</div>
      <div class="p-3 flex gap-2 items-center flex-wrap">
        <input type="file" @change="onFinishedFileChange" class="input w-72" />
        <button @click="uploadFinishedExcel" class="btn btn-primary">업로드</button>
        <button @click="openBomModal" class="btn btn-secondary">BOM 등록</button>
      </div>
    </div>

    <!-- 제품 목록 -->
    <div class="panel overflow-visible">
      <div class="p-3 border-b bg-slate-50 flex flex-wrap items-center gap-3">
        <div class="flex items-center gap-2">
          <button
            @click="listMode = 'FINISHED'"
            :class="listMode === 'FINISHED' ? 'btn btn-primary' : 'btn btn-secondary'"
          >
            완제품
          </button>
          <button
            @click="listMode = 'ALL'"
            :class="listMode === 'ALL' ? 'btn btn-primary' : 'btn btn-secondary'"
          >
            전체
          </button>
        </div>

        <div class="relative w-56" @click.stop>
          <input
            v-model="productSearchInput"
            @focus="showNameDropdown = true"
            @blur="deferHide(() => showNameDropdown = false)"
            placeholder="품번/제품명 검색"
            class="input w-full"
          />
          <div
            v-if="showNameDropdown && filteredNameSuggestions.length"
            class="absolute bg-white border w-full z-10 max-h-40 overflow-y-auto rounded-lg shadow"
          >
            <div
              v-for="item in filteredNameSuggestions"
              :key="`name-${item.code}`"
              @click="selectNameSuggestion(item)"
              class="p-2 hover:bg-slate-100 cursor-pointer text-sm"
            >
              {{ item.name }} ({{ item.code }} / {{ item.old_code || "-" }})
            </div>
          </div>
        </div>
        <button @click="applySearch" class="btn btn-secondary h-9">
          검색
        </button>
      </div>

      <table class="w-full text-left">

        <thead class="table-head">
          <tr>
            <th class="p-3">구품번</th>
            <th class="p-3">신품번</th>
            <th class="p-3">제품명</th>
            <th class="p-3">규격</th>
          </tr>
        </thead>

        <tbody>
          <template v-for="p in filteredProducts" :key="p.code">
            <tr class="border-t cursor-pointer hover:bg-slate-50/70" @click="toggleBOM(p.code)">

            <td class="p-3 font-semibold">
              {{ p.old_code || "-" }}
            </td>
            <td class="p-3">
              <button class="text-left font-semibold text-slate-900 hover:underline"
                @click.stop="toggleBOM(p.code)">
                {{ p.code }}
              </button>
            </td>
            <td class="p-3">
              <button class="text-left text-slate-700 hover:underline"
                @click.stop="toggleBOM(p.code)">
                {{ p.name }}
              </button>
            </td>
            <td class="p-3">{{ p.spec || "-" }}</td>
            </tr>

            <tr v-if="expandedBOM[p.code]" class="border-t bg-slate-50/70">
              <td colspan="4" class="p-3">
                <div class="panel bg-white/60">
                  <div class="panel-header flex items-center justify-between">
                    <span>BOM</span>
                    <button
                      @click.stop="deleteProduct(p.code)"
                      class="btn btn-danger h-8 px-2 text-xs"
                    >
                      삭제
                    </button>
                  </div>
                  <div class="p-3">
                    <div v-if="getBOM(p.code).length" class="overflow-x-auto">
                      <table class="w-full text-sm text-left">
                        <thead class="bg-slate-100 text-slate-600">
                          <tr>
                            <th class="p-2">구품번</th>
                            <th class="p-2">신품번</th>
                            <th class="p-2">품명</th>
                            <th class="p-2">재질</th>
                            <th class="p-2">규격</th>
                            <th class="p-2">현재 재고</th>
                            <th class="p-2">소요량</th>
                            <th class="p-2">관리</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr
                            v-for="b in getBOM(p.code)"
                            :key="b.id"
                            class="border-t"
                          >
                            <template v-if="bomEditState[b.id]">
                              <td class="p-2">{{ getProductByCode(bomEditState[b.id].partCode)?.old_code || "-" }}</td>
                              <td class="p-2">{{ bomEditState[b.id].partCode || "-" }}</td>
                              <td class="p-2" colspan="3">
                                <div class="relative" @click.stop>
                                  <input
                                    v-model="bomEditState[b.id].partInput"
                                    @input="showBomPartDropdown[`edit-${b.id}`] = true"
                                    @focus="showBomPartDropdown[`edit-${b.id}`] = true"
                                    @blur="deferHide(() => showBomPartDropdown[`edit-${b.id}`] = false)"
                                    placeholder="부품 검색 (구/신품번/품명)"
                                    class="input w-full text-xs"
                                  />
                                  <div
                                    v-if="showBomPartDropdown[`edit-${b.id}`] && filteredBomEditParts(b.id).length"
                                    class="absolute bg-white border w-full z-20 max-h-40 overflow-y-auto shadow rounded-lg"
                                  >
                                    <div
                                      v-for="part in filteredBomEditParts(b.id)"
                                      :key="`bom-edit-${b.id}-${part.code}`"
                                      @click="selectBomEditPart(b.id, part)"
                                      class="p-2 hover:bg-slate-100 cursor-pointer text-sm"
                                    >
                                      {{ part.name }} ({{ part.code }} / {{ part.old_code || "-" }})
                                    </div>
                                  </div>
                                </div>
                              </td>
                              <td class="p-2">{{ getProductByCode(bomEditState[b.id].partCode)?.quantity ?? 0 }}</td>
                              <td class="p-2">
                                <input
                                  v-model="bomEditState[b.id].qty"
                                  type="number"
                                  min="1"
                                  class="input w-20 text-xs"
                                />
                              </td>
                            </template>
                            <template v-else>
                              <td class="p-2">{{ getProductByCode(b.child_code)?.old_code || "-" }}</td>
                              <td class="p-2">{{ b.child_code }}</td>
                              <td class="p-2">{{ getProductByCode(b.child_code)?.name || "-" }}</td>
                              <td class="p-2">{{ getProductByCode(b.child_code)?.material || "-" }}</td>
                              <td class="p-2">{{ getProductByCode(b.child_code)?.spec || "-" }}</td>
                              <td class="p-2">{{ getProductByCode(b.child_code)?.quantity ?? 0 }}</td>
                              <td class="p-2">{{ b.quantity }}</td>
                            </template>
                            <td class="p-2">
                              <div class="flex gap-1">
                                <template v-if="bomEditState[b.id]">
                                  <button @click="saveBomEdit(b)"
                                    class="btn btn-primary h-7 px-2 text-xs">
                                    저장
                                  </button>
                                  <button @click="cancelBomEdit(b.id)"
                                    class="btn btn-secondary h-7 px-2 text-xs">
                                    취소
                                  </button>
                                </template>
                                <template v-else>
                                  <button @click="startBomEdit(b)"
                                    class="btn btn-info h-7 px-2 text-xs">
                                    수정
                                  </button>
                                  <button @click="deleteBOM(b.id)"
                                    class="btn btn-danger h-7 px-2 text-xs">
                                    삭제
                                  </button>
                                </template>
                              </div>
                            </td>
                          </tr>
                        </tbody>
                      </table>
                    </div>

                    <div class="flex gap-1 mt-2">
                      <div class="relative" @click.stop>
                        <input
                          v-model="searchInput[p.code]"
                          @focus="showDropdown[p.code] = true"
                          @blur="deferHide(() => showDropdown[p.code] = false)"
                          placeholder="부품 검색"
                          class="input h-7 w-28 text-xs"
                        />
                        <div
                          v-if="showDropdown[p.code]"
                          @mousedown.prevent
                          class="absolute bg-white border w-full max-h-40 overflow-y-auto z-20 shadow rounded"
                        >
                          <div
                            v-for="item in filteredParts(p.code)"
                            :key="item.code"
                            @mousedown.prevent
                            @click="selectPart(p.code, item.code)"
                            class="p-1 hover:bg-slate-100 cursor-pointer text-xs"
                          >
                            {{ item.name }} ({{ item.code }})
                          </div>
                        </div>
                      </div>

                      <input
                        v-model="(bomInput[p.code] ||= {}).qty"
                        type="number"
                        placeholder="수량"
                        class="input h-7 w-16 text-xs"
                      />

                      <button @click="addBOM(p.code)"
                        class="btn btn-primary h-7 px-2 text-xs">
                        +
                      </button>
                    </div>

                    <div v-if="getBOM(p.code).length === 0" class="text-xs text-slate-400 mt-2">
                      BOM 정보가 없습니다.
                    </div>
                  </div>
                </div>
              </td>
            </tr>
          </template>
        </tbody>

      </table>

      <div
        v-if="filteredProducts.length === 0"
        class="p-4 text-sm text-gray-500"
      >
        검색 결과가 없습니다.
      </div>
    </div>

    <!-- BOM 등록 모달 -->
    <div v-if="showBomModal" class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-black/40" @click="showBomModal = false"></div>
      <div class="relative bg-white w-[90vw] max-w-xl rounded-2xl shadow-xl overflow-hidden">
        <div class="flex items-center justify-between px-4 py-3 border-b">
          <div class="font-semibold">BOM 등록</div>
          <div class="flex items-center gap-2">
            <button class="btn btn-secondary" @click="showBomModal = false">닫기</button>
            <button class="btn btn-primary" @click="saveBomModal">저장</button>
          </div>
        </div>
        <div class="p-4 flex flex-col gap-3">
          <div class="relative" @click.stop>
            <input
              v-model="bomParentInput"
              @input="showBomParentDropdown = true"
              @focus="showBomParentDropdown = true"
              @blur="deferHide(() => showBomParentDropdown = false)"
              placeholder="완제품 검색 (품번/제품명)"
              class="input w-full"
            />
            <div
              v-if="showBomParentDropdown && filteredBomParents.length"
              class="absolute bg-white border w-full z-20 max-h-40 overflow-y-auto shadow rounded-lg"
            >
              <div
                v-for="p in filteredBomParents"
                :key="`bom-parent-${p.code}`"
                @click="selectBomParent(p)"
                class="p-2 hover:bg-slate-100 cursor-pointer text-sm"
              >
                {{ p.name }} ({{ p.code }} / {{ p.old_code || "-" }})
              </div>
            </div>
          </div>

          <div class="relative" @click.stop>
            <input
              v-model="bomQuickSearch"
              @focus="showBomPartDropdown.quick = true"
              placeholder="단품 간편 검색 (체크로 추가)"
              class="input w-full"
            />
            <div
              v-if="showBomPartDropdown.quick && filteredBomQuickParts.length"
              class="absolute bg-white border w-full z-20 max-h-52 overflow-y-auto shadow rounded-lg"
              @click.stop
            >
              <div
                v-for="p in filteredBomQuickParts"
                :key="`quick-${p.code}`"
                class="flex items-center gap-2 p-2 hover:bg-slate-100 cursor-pointer text-sm"
                @mousedown.prevent
                @click="toggleBomQuickPart(p)"
              >
                <input type="checkbox" class="h-4 w-4" :checked="isBomQuickChecked(p.code)" />
                <span>{{ p.name }} ({{ p.code }} / {{ p.old_code || "-" }})</span>
              </div>
            </div>
          </div>

          <div class="grid grid-cols-[48px_1fr_140px] gap-2 items-center text-xs text-slate-500">
            <div>#</div>
            <div>부품</div>
            <div>수량</div>
          </div>

          <div
            v-for="(row, idx) in bomRows"
            :key="`bom-row-${idx}`"
            class="grid grid-cols-[48px_1fr_140px] gap-2 items-center"
          >
            <div class="text-xs text-slate-500">{{ idx + 1 }}</div>
            <div class="relative" @click.stop>
              <input
                v-model="row.partInput"
                @input="showBomPartDropdown[idx] = true"
                @focus="showBomPartDropdown[idx] = true"
                @blur="deferHide(() => showBomPartDropdown[idx] = false)"
                placeholder="부품 검색 (품번/제품명)"
                class="input w-full"
              />
              <div
                v-if="showBomPartDropdown[idx] && filteredBomParts(row).length"
                class="absolute bg-white border w-full z-20 max-h-40 overflow-y-auto shadow rounded-lg"
              >
                <div
                  v-for="p in filteredBomParts(row)"
                  :key="`bom-part-${idx}-${p.code}`"
                  @click="selectBomPart(idx, p)"
                  class="p-2 hover:bg-slate-100 cursor-pointer text-sm"
                >
                  {{ p.name }} ({{ p.code }} / {{ p.old_code || "-" }})
                </div>
              </div>
            </div>
            <input
              v-model="row.qty"
              type="number"
              min="1"
              placeholder="수량"
              class="input w-full"
            />
          </div>

          <div class="flex items-center justify-between pt-2">
            <button class="btn btn-secondary" @click="addBomRowsPrompt">줄 추가</button>
            <div class="text-xs text-slate-500">기본 5줄 제공</div>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>
