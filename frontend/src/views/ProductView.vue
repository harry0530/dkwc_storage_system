<script setup>
import { ref, onMounted, computed, watch } from "vue";
import api from "../api";

const products = ref([]);
const boms = ref([]);
const companies = ref([]);

// 제품 입력
const code = ref("");
const name = ref("");
const type = ref("PART");
const location = ref("");
const min_stock = ref("");

// 발주처 선택
const supplierCompanyId = ref("");

// BOM 입력 상태
const bomInput = ref({});
const searchInput = ref({});
const showDropdown = ref({});
const productSearch = ref("");
const productSearchInput = ref("");
const listMode = ref("FINISHED");
const showNameDropdown = ref(false);

// 등록 입력 추천
const showCreateCodeDropdown = ref(false);
const showCreateNameDropdown = ref(false);
const finishedUploadFile = ref(null);

// 완제품 품번 구성 (1 / 01 / M - S)
const finishedFirst = ref("1");
const finishedTwo = ref("01");
const finishedMid = ref("M");
const finishedLast = ref("S");

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
      location: (location.value || "").trim(),
      min_stock: Number(min_stock.value),
      old_code: "",
      material: "",
      spec: "",
      supplier_company_id: supplierCompanyId.value
        ? Number(supplierCompanyId.value)
        : null
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
            location: (location.value || existing.location || "").trim(),
            min_stock: Number(min_stock.value || existing.min_stock || 0)
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
  name.value = "";
  location.value = "";
  min_stock.value = "";
  supplierCompanyId.value = "";

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

// =====================
// 자동완성 필터
// =====================
const filteredParts = (parent_code) => {
  const keyword = searchInput.value[parent_code] || "";

  return products.value.filter(p =>
    p.type === "PART" &&
    (p.code.includes(keyword) || p.name.includes(keyword))
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

const filteredProducts = computed(() => {
  const keyword = (productSearch.value || "").trim().toLowerCase();
  const base =
    listMode.value === "ALL"
      ? products.value
      : products.value.filter((p) => p.type === "FINISHED");
  const sorted = [...base].sort((a, b) =>
    (a.code || "").localeCompare(b.code || "")
  );
  if (!keyword) return listMode.value === "ALL" ? sorted : [];
  return sorted.filter((p) => {
    const codeMatch = (p.code || "").toLowerCase().includes(keyword);
    const nameMatch = (p.name || "").toLowerCase().includes(keyword);
    return codeMatch || nameMatch;
  });
});

onMounted(loadData);

const finishedCode = computed(
  () => `${finishedFirst.value}${finishedTwo.value}${finishedMid.value}-${finishedLast.value}`
);

watch([finishedFirst, finishedTwo, finishedMid, finishedLast], () => {
  productSearchInput.value = finishedCode.value;
  productSearch.value = finishedCode.value;
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
    .filter((p) => (p.name || "").toLowerCase().includes(keyword))
    .slice(0, 10);
});

const selectNameSuggestion = (name) => {
  productSearchInput.value = name;
  productSearch.value = name;
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

const selectCreateNameSuggestion = (nameValue) => {
  name.value = nameValue;
  showCreateNameDropdown.value = false;
};

const onFinishedFileChange = (e) => {
  finishedUploadFile.value = e.target.files?.[0] || null;
};

const uploadFinishedExcel = async () => {
  if (!finishedUploadFile.value) return;
  const form = new FormData();
  form.append("file", finishedUploadFile.value);
  await api.post("/products/import-finished", form, {
    headers: { "Content-Type": "multipart/form-data" }
  });
  finishedUploadFile.value = null;
  loadData();
  alert("엑셀 업로드 완료");
};
</script>

<template>
  <div>

    <h2 class="page-title mb-6">📦 완제품 관리</h2>

    <!-- 제품 등록 -->
    <div class="panel p-3 mb-6 flex gap-2 flex-wrap">

      <div class="relative w-32">
        <input
          v-model="code"
          @focus="showCreateCodeDropdown = true"
          @blur="setTimeout(() => showCreateCodeDropdown = false, 200)"
          placeholder="품번"
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
      <div class="relative w-32">
        <input
          v-model="name"
          @focus="showCreateNameDropdown = true"
          @blur="setTimeout(() => showCreateNameDropdown = false, 200)"
          placeholder="제품명"
          class="input w-full"
        />
        <div
          v-if="showCreateNameDropdown && filteredCreateNameSuggestions.length"
          class="absolute bg-white border w-full z-20 max-h-40 overflow-y-auto shadow rounded-lg"
        >
          <div
            v-for="item in filteredCreateNameSuggestions"
            :key="`create-name-${item.code}`"
            @click="selectCreateNameSuggestion(item.name)"
            class="p-2 hover:bg-slate-100 cursor-pointer text-sm"
          >
            {{ item.name }} ({{ item.code }})
          </div>
        </div>
      </div>

      <select v-model="type" class="input">
        <option value="PART">부품</option>
        <option value="FINISHED">완제품</option>
      </select>

      <input v-model="location" placeholder="위치" class="input w-32" />
      <input v-model="min_stock" type="number" placeholder="최소재고" class="input w-24" />

      <select v-model="supplierCompanyId" class="input w-40">
        <option value="">발주처 선택</option>
        <option v-for="c in companies" :key="c.id" :value="c.id">
          {{ c.name }}
        </option>
      </select>

      <button @click="createProduct" class="btn btn-primary">
        제품 등록
      </button>

    </div>

    <div class="panel mb-6">
      <div class="panel-header">완제품 엑셀 업로드</div>
      <div class="p-3 flex gap-2 items-center flex-wrap">
        <input type="file" @change="onFinishedFileChange" class="input w-72" />
        <button @click="uploadFinishedExcel" class="btn btn-primary">업로드</button>
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

        <div class="relative w-56">
          <input
            v-model="productSearchInput"
            @focus="showNameDropdown = true"
            @blur="setTimeout(() => showNameDropdown = false, 200)"
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
              @click="selectNameSuggestion(item.name)"
              class="p-2 hover:bg-slate-100 cursor-pointer text-sm"
            >
              {{ item.name }} ({{ item.code }})
            </div>
          </div>
        </div>
        <button @click="applySearch" class="btn btn-secondary h-9">
          검색
        </button>
        <div class="flex items-center gap-1">
          <select v-model="finishedFirst" class="input w-16">
            <option v-for="n in [1,2,3,4,5]" :key="n" :value="String(n)">
              {{ n }}
            </option>
          </select>
          <select v-model="finishedTwo" class="input w-20">
            <option v-for="n in 21" :key="n" :value="String(n).padStart(2, '0')">
              {{ String(n).padStart(2, '0') }}
            </option>
          </select>
          <select v-model="finishedMid" class="input w-16">
            <option value="M">M</option>
            <option value="S">S</option>
          </select>
          <select v-model="finishedLast" class="input w-16">
            <option value="S">S</option>
            <option value="E">E</option>
            <option value="T">T</option>
            <option value="K">K</option>
          </select>
        </div>
      </div>

      <table class="w-full text-left">

        <thead class="table-head">
          <tr>
            <th class="p-3">제품</th>
            <th class="p-3">위치</th>
            <th class="p-3">최소재고</th>
            <th class="p-3">발주처</th>
            <th class="p-3">BOM</th>
            <th class="p-3">삭제</th>
          </tr>
        </thead>

        <tbody>
          <tr v-for="p in filteredProducts" :key="p.code" class="border-t">

            <!-- 제품 -->
            <td class="p-3 font-semibold">
              {{ p.name }} ({{ p.code }})
            </td>

            <td class="p-3">{{ p.location }}</td>
            <td class="p-3">{{ p.min_stock }}</td>

            <!-- 발주처 -->
            <td class="p-3">
              <span class="text-sm text-slate-700">
                {{ companies.find(c => c.id === p.supplier_company_id)?.name || "-" }}
              </span>
            </td>

            <!-- ⭐ BOM -->
            <td class="p-3">

              <!-- BOM 리스트 -->
              <div
                v-for="b in getBOM(p.code)"
                :key="b.id"
                class="flex items-center gap-2 text-sm"
              >
                {{ b.child_code }} x {{ b.quantity }}

                <button @click="deleteBOM(b.id)"
                  class="btn btn-danger h-7 px-2 text-xs">
                  삭제
                </button>
              </div>

              <!-- BOM 추가 -->
              <div class="flex gap-1 mt-1">

                <div class="relative">

                  <input
                    v-model="searchInput[p.code]"
                    @focus="showDropdown[p.code] = true"
                    @blur="setTimeout(() => showDropdown[p.code] = false, 200)"
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

            </td>

            <td class="p-3">
              <button
                @click="deleteProduct(p.code)"
                class="btn btn-danger h-8 px-2 text-xs"
              >
                삭제
              </button>
            </td>

          </tr>
        </tbody>

      </table>

      <div
        v-if="filteredProducts.length === 0"
        class="p-4 text-sm text-gray-500"
      >
        검색 결과가 없습니다.
      </div>
    </div>

  </div>
</template>
