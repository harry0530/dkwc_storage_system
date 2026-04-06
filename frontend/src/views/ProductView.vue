<script setup>
import { ref, onMounted, computed } from "vue";
import api from "../api";

const products = ref([]);
const aliases = ref([]);
const boms = ref([]);
const companies = ref([]);

// 제품 입력
const code = ref("");
const name = ref("");
const type = ref("PART");
const location = ref("");
const min_stock = ref("");

// alias 입력
const alias_company = ref("");
const alias_code = ref("");
const selected_product_code = ref("");
const showCompanyDropdown = ref(false);

// BOM 입력 상태
const bomInput = ref({});
const searchInput = ref({});
const showDropdown = ref({});
const productSearch = ref("");

// alias 수정
const editingAliasId = ref("");
const editAliasCompany = ref("");
const editAliasCode = ref("");

// =====================
// 데이터 로드
// =====================
const loadData = async () => {
  const p = await api.get("/products/");
  const a = await api.get("/product-alias/");
  const b = await api.get("/bom/");
  const c = await api.get("/companies/");

  products.value = p.data;
  aliases.value = a.data;
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
    min_stock: Number(min_stock.value)
    });
  } catch (err) {
    const message =
      err?.response?.data?.detail || "등록 실패: 품번 중복 여부를 확인하세요.";
    alert(message);
    return;
  }

  code.value = "";
  name.value = "";
  location.value = "";
  min_stock.value = "";

  loadData();
};

// =====================
// alias 등록
// =====================
const createAlias = async () => {
  if (!selected_product_code.value || !alias_company.value || !alias_code.value) return;

  await api.post("/product-alias/", {
    product_code: selected_product_code.value,
    company: alias_company.value,
    alias_code: alias_code.value
  });

  alias_company.value = "";
  alias_code.value = "";

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
  const base = products.value.filter((p) => p.type === "FINISHED");
  if (!keyword) return base;
  return base.filter((p) =>
    (p.code || "").toLowerCase().includes(keyword) ||
    (p.name || "").toLowerCase().includes(keyword)
  );
});

const filteredCompanies = computed(() => {
  const keyword = (alias_company.value || "").trim().toLowerCase();
  return companies.value.filter((c) =>
    (c.name || "").toLowerCase().includes(keyword)
  );
});

const selectCompany = (name) => {
  alias_company.value = name;
  showCompanyDropdown.value = false;
};

const startEditAlias = (alias) => {
  editingAliasId.value = String(alias.id);
  editAliasCompany.value = alias.company || "";
  editAliasCode.value = alias.alias_code || "";
};

const cancelEditAlias = () => {
  editingAliasId.value = "";
  editAliasCompany.value = "";
  editAliasCode.value = "";
};

const saveEditAlias = async (aliasId) => {
  await api.put(`/product-alias/${aliasId}`, {
    company: editAliasCompany.value,
    alias_code: editAliasCode.value
  });
  cancelEditAlias();
  loadData();
};

const deleteAlias = async (aliasId) => {
  const ok = window.confirm("해당 회사 품번을 삭제할까요?");
  if (!ok) return;
  await api.delete(`/product-alias/${aliasId}`);
  loadData();
};

onMounted(loadData);
</script>

<template>
  <div>

    <h2 class="page-title mb-6">📦 상품 + BOM 관리</h2>

    <!-- 제품 등록 -->
    <div class="panel p-3 mb-6 flex gap-2 flex-wrap">

      <input v-model="code" placeholder="품번" class="input w-32" />
      <input v-model="name" placeholder="제품명" class="input w-32" />

      <select v-model="type" class="input">
        <option value="PART">부품</option>
        <option value="FINISHED">완제품</option>
      </select>

      <input v-model="location" placeholder="위치" class="input w-32" />
      <input v-model="min_stock" type="number" placeholder="최소재고" class="input w-24" />

      <button @click="createProduct" class="btn btn-primary">
        제품 등록
      </button>

    </div>

    <!-- alias 등록 -->
    <div class="panel p-3 mb-6 flex gap-2 flex-wrap">

      <select v-model="selected_product_code" class="input w-40">
        <option value="">제품 선택</option>
        <option v-for="p in products.filter(x => x.type === 'FINISHED')" :key="p.code" :value="p.code">
          {{ p.name }} ({{ p.code }})
        </option>
      </select>

      <div class="relative w-32">
        <input
          v-model="alias_company"
          @focus="showCompanyDropdown = true"
          @blur="setTimeout(() => showCompanyDropdown = false, 200)"
          placeholder="회사"
          class="input w-full"
        />
        <div
          v-if="showCompanyDropdown"
          @mousedown.prevent
          class="absolute bg-white border w-full z-20 max-h-40 overflow-y-auto shadow rounded-lg"
        >
          <div
            v-for="c in filteredCompanies"
            :key="c.id"
            @mousedown.prevent
            @click="selectCompany(c.name)"
            class="p-2 hover:bg-slate-100 cursor-pointer text-sm"
          >
            {{ c.name }}
          </div>
        </div>
      </div>
      <input v-model="alias_code" placeholder="회사 품번" class="input w-32" />

      <button @click="createAlias" class="btn btn-success">
        품번 추가
      </button>

    </div>

    <!-- 제품 목록 -->
    <div class="panel overflow-visible">
      <div class="p-3 border-b bg-slate-50 flex flex-wrap items-center gap-3">
        <input
          v-model="productSearch"
          placeholder="품번/제품명 검색"
          class="input w-56"
        />
      </div>

      <table class="w-full text-left">

        <thead class="table-head">
          <tr>
            <th class="p-3">제품</th>
            <th class="p-3">위치</th>
            <th class="p-3">최소재고</th>
            <th class="p-3">회사별 품번</th>
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

            <!-- alias -->
            <td class="p-3">
              <div
                v-for="a in aliases.filter(x => x.product_code === p.code)"
                :key="a.id"
                class="text-sm flex items-center gap-2"
              >
                <template v-if="editingAliasId === String(a.id)">
                  <input
                    v-model="editAliasCompany"
                    class="input h-7 px-2 text-xs w-20"
                  />
                  <span class="text-xs text-gray-400">→</span>
                  <input
                    v-model="editAliasCode"
                    class="input h-7 px-2 text-xs w-24"
                  />
                  <button @click="saveEditAlias(a.id)"
                    class="btn btn-info h-7 px-2 text-xs">
                    저장
                  </button>
                  <button @click="cancelEditAlias"
                    class="btn btn-secondary h-7 px-2 text-xs">
                    취소
                  </button>
                </template>
                <template v-else>
                  <span>{{ a.company }} → {{ a.alias_code }}</span>
                  <button @click="startEditAlias(a)"
                    class="btn btn-info h-7 px-2 text-xs">
                    수정
                  </button>
                  <button @click="deleteAlias(a.id)"
                    class="btn btn-danger h-7 px-2 text-xs">
                    삭제
                  </button>
                </template>
              </div>
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
