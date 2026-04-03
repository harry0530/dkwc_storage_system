<script setup>
import { ref, onMounted, computed } from "vue";
import api from "../api";

const products = ref([]);
const aliases = ref([]);
const boms = ref([]);

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

// BOM 입력 상태
const bomInput = ref({});
const searchInput = ref({});
const showDropdown = ref({});
const productSearch = ref("");

// =====================
// 데이터 로드
// =====================
const loadData = async () => {
  const p = await api.get("/products/");
  const a = await api.get("/product-alias/");
  const b = await api.get("/bom/");

  products.value = p.data;
  aliases.value = a.data;
  boms.value = b.data;
};

// =====================
// 제품 등록
// =====================
const createProduct = async () => {
  if (!code.value) return alert("품번 입력");

  await api.post("/products/", {
    code: code.value,
    name: name.value,
    type: type.value,
    location: location.value,
    min_stock: Number(min_stock.value)
  });

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
  if (!selected_product_code.value) return;

  await api.post("/product-alias/", {
    product_code: selected_product_code.value,
    company: alias_company.value,
    alias_code: alias_code.value
  });

  alias_company.value = "";
  alias_code.value = "";

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
    p.code.includes(keyword) || p.name.includes(keyword)
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
  if (!keyword) return products.value;
  return products.value.filter((p) =>
    (p.code || "").toLowerCase().includes(keyword) ||
    (p.name || "").toLowerCase().includes(keyword)
  );
});

onMounted(loadData);
</script>

<template>
  <div>

    <h2 class="text-3xl font-bold mb-6">📦 상품 + BOM 관리</h2>

    <!-- 제품 등록 -->
    <div class="bg-white shadow rounded-xl p-3 mb-6 flex gap-2 flex-wrap">

      <input v-model="code" placeholder="품번" class="border px-2 py-1 h-9 rounded w-32" />
      <input v-model="name" placeholder="제품명" class="border px-2 py-1 h-9 rounded w-32" />

      <select v-model="type" class="border px-2 py-1 h-9 rounded">
        <option value="PART">부품</option>
        <option value="FINISHED">완제품</option>
      </select>

      <input v-model="location" placeholder="위치" class="border px-2 py-1 h-9 rounded w-32" />
      <input v-model="min_stock" type="number" placeholder="최소재고" class="border px-2 py-1 h-9 rounded w-24" />

      <button @click="createProduct" class="bg-blue-500 text-white px-3 h-9 rounded">
        제품 등록
      </button>

    </div>

    <!-- alias 등록 -->
    <div class="bg-white shadow rounded-xl p-3 mb-6 flex gap-2 flex-wrap">

      <select v-model="selected_product_code" class="border px-2 py-1 h-9 rounded w-40">
        <option value="">제품 선택</option>
        <option v-for="p in products" :key="p.code" :value="p.code">
          {{ p.name }} ({{ p.code }})
        </option>
      </select>

      <input v-model="alias_company" placeholder="회사" class="border px-2 py-1 h-9 rounded w-32" />
      <input v-model="alias_code" placeholder="회사 품번" class="border px-2 py-1 h-9 rounded w-32" />

      <button @click="createAlias" class="bg-green-500 text-white px-3 h-9 rounded">
        품번 추가
      </button>

    </div>

    <!-- 제품 목록 -->
    <div class="bg-white shadow rounded-xl overflow-hidden">
      <div class="p-3 border-b bg-gray-50">
        <input
          v-model="productSearch"
          placeholder="품번/제품명 검색"
          class="border px-2 py-1 h-9 rounded w-56 text-sm"
        />
      </div>

      <table class="w-full text-left">

        <thead class="bg-gray-100">
          <tr>
            <th class="p-3">제품</th>
            <th class="p-3">위치</th>
            <th class="p-3">최소재고</th>
            <th class="p-3">회사별 품번</th>
            <th class="p-3">BOM</th>
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
                class="text-sm"
              >
                {{ a.company }} → {{ a.alias_code }}
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
                  class="bg-red-500 text-white px-1 rounded text-xs">
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
                    class="border px-1 py-0.5 w-28 text-xs"
                  />

                  <div v-if="showDropdown[p.code]"
                    class="absolute bg-white border w-full max-h-32 overflow-y-auto z-10">

                    <div
                      v-for="item in filteredParts(p.code)"
                      :key="item.code"
                      @click="selectPart(p.code, item.code)"
                      class="p-1 hover:bg-gray-100 cursor-pointer text-xs"
                    >
                      {{ item.name }} ({{ item.code }})
                    </div>

                  </div>

                </div>

                <input
                  v-model="(bomInput[p.code] ||= {}).qty"
                  type="number"
                  placeholder="수량"
                  class="border px-1 py-0.5 w-16 text-xs"
                />

                <button @click="addBOM(p.code)"
                  class="bg-blue-500 text-white px-1 text-xs">
                  +
                </button>

              </div>

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
