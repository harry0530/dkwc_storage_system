<script setup>
import { ref, onMounted, computed } from "vue";
import api from "../api";

const orders = ref([]);
const products = ref([]);
const companies = ref([]);
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
const showCompleted = ref(false);

// 견적 이메일
const showQuoteModal = ref(false);
const quoteTo = ref("");
const quoteSubject = ref("");
const quoteBody = ref("");

// ⭐ 공통 문자열 정리 함수 (핵심)
const clean = (v) => (v || "").trim().toLowerCase();

// =====================
// 데이터 로드
// =====================
const loadAll = async () => {
  const o = await api.get("/orders/");
  const p = await api.get("/products/");
  const c = await api.get("/companies/");
  const b = await api.get("/bom/");
  const i = await api.get("/inventory/");

  orders.value = o.data;
  products.value = p.data.map((item) => ({
    ...item,
    code: item.new_code || item.code || "",
    old_code: item.old_code || ""
  }));
  companies.value = c.data;
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

  const productByNew = products.value.find(p =>
    clean(p.code) === cleanInput
  );
  const productByOld = products.value.find(p =>
    clean(p.old_code) === cleanInput
  );

  let realCode = inputCode;
  let fromOld = false;
  if (productByNew) {
    realCode = productByNew.code;
  } else if (productByOld) {
    realCode = productByOld.code;
    fromOld = true;
  }

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
  displayProduct.value = fromOld
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
  selectedCompany.value = name.name || name;
  companyInput.value = name.name || name;
  showCompanyDropdown.value = false;

  const match = companies.value.find((c) => c.name === companyInput.value);
  if (match?.email) {
    quoteTo.value = match.email;
  }
  updateProductName();
};

// =====================
// 품번 자동완성
// =====================
const showCodeDropdown = ref(false);

const filteredCodes = computed(() => {
  const keyword = (codeInput.value || "").trim().toLowerCase();
  const list = [];

  for (const p of products.value) {
    if (p.code && (!keyword || p.code.toLowerCase().includes(keyword))) {
      list.push({
        key: `new-${p.code}`,
        code: p.code,
        label: `${p.code} (신품번)`
      });
    }
    if (p.old_code && (!keyword || p.old_code.toLowerCase().includes(keyword))) {
      list.push({
        key: `old-${p.old_code}`,
        code: p.old_code,
        label: `${p.old_code} (구품번)`
      });
    }
  }

  return list;
});

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

const buildQuoteBody = () => {
  const companyName = selectedCompany.value || companyInput.value || "";
  const productLabel = displayProduct.value || (selectedCode.value || codeInput.value || "");
  const qty = quantity.value || "";
  return [
    `안녕하세요 ${companyName} 담당자님,`,
    "",
    "아래와 같이 견적드립니다.",
    `- 품목: ${productLabel}`,
    `- 수량: ${qty || "-"}`,
    "",
    "검토 부탁드립니다.",
    "",
    "감사합니다."
  ].join("\n");
};

const openQuoteModal = () => {
  showQuoteModal.value = true;
  const match = companies.value.find((c) => c.name === (selectedCompany.value || companyInput.value));
  if (!quoteTo.value) quoteTo.value = match?.email || "";
  if (!quoteSubject.value) {
    const base = displayProduct.value || (selectedCode.value || codeInput.value || "");
    quoteSubject.value = base ? `견적서 - ${base}` : "견적서";
  }
  if (!quoteBody.value) {
    quoteBody.value = buildQuoteBody();
  }
};

const fillQuoteBody = () => {
  quoteBody.value = buildQuoteBody();
};

const sendQuoteEmail = async () => {
  if (!quoteTo.value.trim()) return alert("받는 이메일을 입력하세요.");
  if (!quoteSubject.value.trim()) return alert("제목을 입력하세요.");
  if (!quoteBody.value.trim()) return alert("본문을 입력하세요.");

  await api.post("/orders/quote-email", {
    to: quoteTo.value,
    subject: quoteSubject.value,
    body: quoteBody.value
  });
  alert("메일 전송 완료");
  showQuoteModal.value = false;
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

const pendingOrders = computed(() =>
  orders.value.filter((o) => o.status === "WAIT")
);

const completedOrders = computed(() =>
  orders.value.filter((o) => o.status === "DONE")
);

const visibleOrders = computed(() =>
  showCompleted.value ? completedOrders.value : pendingOrders.value
);

const deleteOrder = async (id) => {
  const ok = window.confirm("주문을 삭제(거부)할까요?");
  if (!ok) return;
  await api.delete(`/orders/${id}`);
  loadAll();
};
</script>

<template>
  <div>

    <div class="flex items-center justify-between mb-6">
      <h2 class="page-title">📋 주문 관리</h2>
      <button
        @click="showCompleted = !showCompleted"
        class="btn btn-secondary"
      >
        {{ showCompleted ? "대기목록 보기" : "완료내역 보기" }}
      </button>
    </div>

    <div class="panel p-3 mb-6 flex gap-3 items-center flex-wrap">

      <div class="relative w-40">
        <input
          v-model="companyInput"
          @input="updateProductName"
          @focus="showCompanyDropdown = true"
          @blur="setTimeout(() => showCompanyDropdown = false, 200)"
          placeholder="회사"
          class="input w-full"
        />
        <div v-if="showCompanyDropdown"
          class="absolute bg-white border w-full z-10 max-h-40 overflow-y-auto rounded-lg shadow">
          <div v-for="c in filteredCompanies"
            :key="c.id"
            @click="selectCompany(c)"
            class="p-2 hover:bg-slate-100 cursor-pointer">
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
          class="input w-full"
        />
        <div v-if="showCodeDropdown"
          class="absolute bg-white border w-full z-10 max-h-40 overflow-y-auto rounded-lg shadow">
          <div v-for="a in filteredCodes"
            :key="a.key"
            @click="selectCode(a.code)"
            class="p-2 hover:bg-slate-100 cursor-pointer">
            {{ a.label }}
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
        class="input w-24" />

      <button @click="createOrder"
        class="btn btn-primary">
        주문 생성
      </button>
      <button @click="openQuoteModal"
        class="btn btn-secondary">
        견적서 이메일
      </button>

    </div>

    <div v-if="stockWarning"
      class="text-red-500 text-sm mb-4">
      ⚠ {{ stockWarning }}
    </div>

    <div class="panel overflow-hidden">
      <table class="w-full text-left">

        <thead class="table-head">
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
          <tr v-for="o in visibleOrders" :key="o.id" class="border-t">

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
                class="btn btn-success h-8 px-2 text-xs">
                생산
              </button>

              <button v-if="o.status === 'WAIT'"
                @click="deleteOrder(o.id)"
                class="btn btn-danger h-8 px-2 text-xs">
                삭제
              </button>

              <button v-if="o.status === 'DONE'"
                @click="undoProduction(o.id)"
                class="btn btn-secondary h-8 px-2 text-xs">
                취소
              </button>
            </td>

          </tr>
        </tbody>

      </table>
    </div>

    <!-- 견적서 이메일 모달 -->
    <div v-if="showQuoteModal" class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-black/40" @click="showQuoteModal = false"></div>
      <div class="relative bg-white w-[90vw] max-w-2xl max-h-[85vh] rounded-2xl shadow-xl overflow-hidden">
        <div class="flex items-center justify-between px-4 py-3 border-b">
          <div class="font-semibold">견적서 이메일</div>
          <button class="btn btn-secondary" @click="showQuoteModal = false">닫기</button>
        </div>
        <div class="p-4 flex flex-col gap-3">
          <input v-model="quoteTo" placeholder="받는 이메일"
            class="input w-full" />
          <input v-model="quoteSubject" placeholder="제목"
            class="input w-full" />
          <textarea v-model="quoteBody" rows="10"
            class="input w-full h-auto"
            placeholder="내용을 입력하세요"></textarea>
          <div class="flex gap-2">
            <button @click="fillQuoteBody" class="btn btn-secondary">
              견적서 자동 작성
            </button>
            <button @click="sendQuoteEmail" class="btn btn-primary">
              이메일 발송
            </button>
          </div>
          <div class="text-xs text-slate-500">
            SMTP 설정이 서버에 필요합니다.
          </div>
        </div>
      </div>
    </div>

  </div>
</template>
