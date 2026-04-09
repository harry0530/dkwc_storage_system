<script setup>
import { ref, onMounted, computed } from "vue";
import api from "../api";

const orders = ref([]);
const purchaseOrders = ref([]);
const purchaseReceipts = ref([]);
const products = ref([]);
const companies = ref([]);
const boms = ref([]);
const inventory = ref([]);

const activeTab = ref("incoming");

const companyInput = ref("");
const selectedCompany = ref("");

const codeInput = ref("");
const selectedCode = ref("");

const quantity = ref("");

const purchaseCompanyInput = ref("");
const purchaseSelectedCompany = ref("");
const showPurchaseModal = ref(false);
const purchaseRows = ref([]);
const purchaseRowDropdown = ref({});

// 표시
const displayProduct = ref("");
const stockWarning = ref("");
const showCompleted = ref(false);
const showPurchaseCompleted = ref(false);

// 견적 이메일
const showQuoteModal = ref(false);
const quoteTo = ref("");
const quoteSubject = ref("");
const quoteBody = ref("");

// ⭐ 공통 문자열 정리 함수 (핵심)
const clean = (v) => (v || "").trim().toLowerCase();

const resolveProduct = (inputCode) => {
  const raw = (inputCode || "").trim();
  if (!raw) return null;

  const cleanInput = clean(raw);
  const productByNew = products.value.find(p =>
    clean(p.code) === cleanInput
  );
  const productByOld = products.value.find(p =>
    clean(p.old_code) === cleanInput
  );
  const productByNameExact = products.value.find(p =>
    clean(p.name) === cleanInput
  );
  const productByNameLike = products.value.find(p =>
    clean(p.name).includes(cleanInput)
  );

  let realCode = raw;
  let fromOld = false;
  if (productByNew) {
    realCode = productByNew.code;
  } else if (productByOld) {
    realCode = productByOld.code;
    fromOld = true;
  } else if (productByNameExact) {
    realCode = productByNameExact.code;
  } else if (productByNameLike) {
    realCode = productByNameLike.code;
  }

  const product = products.value.find(p =>
    clean(p.code) === clean(realCode)
  );

  if (!product) return null;

  return { product, realCode, fromOld, inputCode: raw };
};

const buildCodeOptions = (keyword) => {
  const list = [];
  const key = (keyword || "").trim().toLowerCase();

  for (const p of products.value) {
    if (p.code && (!key || p.code.toLowerCase().includes(key))) {
      list.push({
        key: `new-${p.code}`,
        code: p.code,
        label: `${p.code} (신품번)`
      });
    }
    if (p.old_code && (!key || p.old_code.toLowerCase().includes(key))) {
      list.push({
        key: `old-${p.old_code}`,
        code: p.old_code,
        label: `${p.old_code} (구품번)`
      });
    }
    if (p.name && (!key || p.name.toLowerCase().includes(key))) {
      list.push({
        key: `name-${p.code}`,
        code: p.code,
        label: `${p.name} (${p.code})`
      });
    }
  }

  return list;
};

// =====================
// 데이터 로드
// =====================
const loadAll = async () => {
  const o = await api.get("/orders/");
  const po = await api.get("/purchase-orders/");
  const pr = await api.get("/purchase-orders/receipts");
  const p = await api.get("/products/");
  const c = await api.get("/companies/");
  const b = await api.get("/bom/");
  const i = await api.get("/inventory/");

  orders.value = o.data;
  purchaseOrders.value = po.data;
  purchaseReceipts.value = pr.data;
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

  const result = resolveProduct(inputCode);
  if (!result) {
    displayProduct.value = "❌ 없는 제품";
    stockWarning.value = "";
    return;
  }

  const { product, realCode, fromOld } = result;
  const cleanReal = clean(realCode);

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

const showPurchaseCompanyDropdown = ref(false);

const filteredPurchaseCompanies = computed(() =>
  companies.value.filter(c =>
    c.name.includes(purchaseCompanyInput.value)
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

const selectPurchaseCompany = (name) => {
  purchaseSelectedCompany.value = name.name || name;
  purchaseCompanyInput.value = name.name || name;
  showPurchaseCompanyDropdown.value = false;
};

// =====================
// 품번 자동완성
// =====================
const showCodeDropdown = ref(false);

const filteredCodes = computed(() => buildCodeOptions(codeInput.value));

const selectCode = (code) => {
  selectedCode.value = code;
  codeInput.value = code;
  showCodeDropdown.value = false;

  updateProductName();
};
const initPurchaseRows = (count = 10) => {
  purchaseRows.value = Array.from({ length: count }, () => ({
    codeInput: "",
    selectedCode: "",
    quantity: ""
  }));
  purchaseRowDropdown.value = {};
};

const openPurchaseModal = () => {
  showPurchaseModal.value = true;
  if (purchaseRows.value.length === 0) {
    initPurchaseRows();
  }
};

const addPurchaseRow = () => {
  purchaseRows.value.push({
    codeInput: "",
    selectedCode: "",
    quantity: ""
  });
};

const filteredPurchaseRowCodes = (row) => buildCodeOptions(row.codeInput);

const selectPurchaseRowCode = (index, code) => {
  const row = purchaseRows.value[index];
  if (!row) return;
  row.selectedCode = code;
  row.codeInput = code;
  purchaseRowDropdown.value[index] = false;
};

// =====================
// 주문 생성
// =====================
const createOrder = async () => {
  const companyName = selectedCompany.value || companyInput.value;
  if (!companyName || !quantity.value) return alert("회사/수량을 입력하세요.");

  if (stockWarning.value) {
    alert("재고 부족 상태입니다!");
    return;
  }

  const result = resolveProduct(selectedCode.value || codeInput.value);
  if (!result) return alert("품번/품명을 확인하세요.");
  const finalCode = result.realCode;

  await api.post("/orders/", {
    product_code: finalCode,
    quantity: Number(quantity.value),
    company: companyName
  });

  // 초기화
  companyInput.value = "";
  codeInput.value = "";
  selectedCode.value = "";
  selectedCompany.value = "";
  displayProduct.value = "";
  stockWarning.value = "";
  quantity.value = "";

  loadAll();
};

// =====================
// 발주 생성 (모달, 다중 품목)
// =====================
const createPurchaseOrders = async () => {
  const companyName = purchaseSelectedCompany.value || purchaseCompanyInput.value;
  if (!companyName) return alert("납품처를 입력하세요.");

  const payloads = [];

  for (let i = 0; i < purchaseRows.value.length; i += 1) {
    const row = purchaseRows.value[i];
    const qty = Number(row.quantity || 0);
    const rawCode = row.selectedCode || row.codeInput;

    if (!rawCode && !qty) continue;
    if (!rawCode || qty <= 0) {
      return alert(`발주 ${i + 1}행의 품번/수량을 확인하세요.`);
    }

    const result = resolveProduct(rawCode);
    if (!result) {
      return alert(`발주 ${i + 1}행의 품번/품명을 확인하세요.`);
    }

    payloads.push({
      product_code: result.realCode,
      quantity: qty,
      company: companyName
    });
  }

  if (payloads.length === 0) {
    return alert("입력된 발주 항목이 없습니다.");
  }

  await api.post("/purchase-orders/batch", {
    company: companyName,
    items: payloads.map((payload) => ({
      product_code: payload.product_code,
      quantity: payload.quantity
    }))
  });

  showPurchaseModal.value = false;
  initPurchaseRows();
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

const completePurchase = async (id) => {
  await api.post(`/purchase-orders/receive-all/${id}`);
  loadAll();
};

const undoPurchase = async (id) => {
  await api.post(`/purchase-orders/undo/${id}`);
  loadAll();
};

const partialPurchase = async (order) => {
  const remaining = (order.quantity || 0) - (order.received_quantity || 0);
  if (remaining <= 0) return alert("잔여 수량이 없습니다.");

  const input = window.prompt(`부분 입고 수량 입력 (잔여 ${remaining})`, String(remaining));
  if (!input) return;

  const qty = Number(input);
  if (!Number.isFinite(qty) || qty <= 0) {
    return alert("수량이 올바르지 않습니다.");
  }
  if (qty > remaining) {
    return alert("잔여 수량보다 클 수 없습니다.");
  }

  await api.post(`/purchase-orders/receive/${order.id}`, {
    quantity: qty
  });
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

const pendingPurchaseOrders = computed(() =>
  purchaseOrders.value.filter((o) => o.status !== "DONE")
);

const completedPurchaseOrders = computed(() =>
  purchaseOrders.value.filter((o) => o.status === "DONE")
);

const visiblePurchaseOrders = computed(() =>
  showPurchaseCompleted.value ? completedPurchaseOrders.value : pendingPurchaseOrders.value
);

const purchaseBatches = computed(() => {
  const map = new Map();

  const rows = Array.isArray(visiblePurchaseOrders.value)
    ? visiblePurchaseOrders.value.filter((o) => o && typeof o === "object")
    : [];

  for (const o of rows) {
    const key = o.batch_id ? `batch-${o.batch_id}` : `single-${o.id}`;
    if (!map.has(key)) {
      map.set(key, {
        key,
        batch_id: o.batch_id || o.id,
        company: o.batch_company || o.company,
        created_at: o.batch_created_at || o.created_at,
        status: o.batch_status || o.status,
        items: []
      });
    }
    map.get(key).items.push(o);
  }

  return Array.from(map.values()).sort((a, b) => (b.batch_id || 0) - (a.batch_id || 0));
});

const formatOrderTime = (dateValue) => {
  if (!dateValue) return "-";
  const raw = String(dateValue).trim();
  const normalized = raw.includes("T") ? raw : raw.replace(" ", "T");
  const withTimezone = /[zZ]|[+\-]\d{2}:\d{2}$/.test(normalized)
    ? normalized
    : `${normalized}Z`;
  const date = new Date(withTimezone);
  if (Number.isNaN(date.getTime())) return "-";
  return new Intl.DateTimeFormat("ko-KR", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    hour12: false
  }).format(date);
};

const receiptMap = computed(() => {
  const map = new Map();
  const rows = Array.isArray(purchaseReceipts.value)
    ? purchaseReceipts.value.filter((r) => r && typeof r === "object")
    : [];
  for (const r of rows) {
    const key = String(r.purchase_order_id);
    if (!map.has(key)) {
      map.set(key, []);
    }
    map.get(key).push(r);
  }
  for (const [key, arr] of map.entries()) {
    arr.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
    map.set(key, arr);
  }
  return map;
});

const showReceipt = ref({});

const receiptKey = (id) => String(id ?? "");

const toggleReceipt = (id) => {
  const key = receiptKey(id);
  showReceipt.value = {
    ...showReceipt.value,
    [key]: !showReceipt.value[key]
  };
};

const deleteOrder = async (id) => {
  const ok = window.confirm("주문을 삭제(거부)할까요?");
  if (!ok) return;
  await api.delete(`/orders/${id}`);
  loadAll();
};

const deletePurchaseOrder = async (id) => {
  const ok = window.confirm("발주를 삭제할까요?");
  if (!ok) return;
  await api.delete(`/purchase-orders/${id}`);
  loadAll();
};
</script>

<template>
  <div>

    <div class="flex items-center gap-2 mb-6">
      <button
        class="btn"
        :class="activeTab === 'incoming' ? 'btn-primary' : 'btn-secondary'"
        @click="activeTab = 'incoming'"
      >
        들어온 주문
      </button>
      <button
        class="btn"
        :class="activeTab === 'purchase' ? 'btn-primary' : 'btn-secondary'"
        @click="activeTab = 'purchase'"
      >
        발주
      </button>
    </div>

    <div v-if="activeTab === 'incoming'">

      <div class="flex items-center justify-between mb-6">
        <h2 class="page-title">📋 주문 관리</h2>
        <button
          @click="showCompleted = !showCompleted"
          class="btn btn-secondary"
        >
          {{ showCompleted ? "대기목록 보기" : "완료내역 보기" }}
        </button>
      </div>

    <div class="panel p-3 mb-6 flex gap-3 items-center flex-wrap overflow-visible">

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
          class="absolute bg-white border w-full z-50 max-h-40 overflow-y-auto rounded-lg shadow">
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
          class="absolute bg-white border w-full z-50 max-h-40 overflow-y-auto rounded-lg shadow">
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

    <div v-else>

      <div class="flex items-center justify-between mb-6">
        <h2 class="page-title">📦 발주 관리</h2>
        <div class="flex items-center gap-2">
          <button
            @click="showPurchaseCompleted = !showPurchaseCompleted"
            class="btn btn-secondary"
          >
            {{ showPurchaseCompleted ? "대기목록 보기" : "완료내역 보기" }}
          </button>
          <button class="btn btn-primary" @click="openPurchaseModal">
            발주 등록
          </button>
        </div>
      </div>

      <div class="panel overflow-hidden">
        <table class="w-full text-left">

          <thead class="table-head">
            <tr>
              <th class="p-3">발주ID</th>
              <th class="p-3">제품</th>
              <th class="p-3">주문수량</th>
              <th class="p-3">입고수량</th>
              <th class="p-3">잔여</th>
              <th class="p-3">최근 입고</th>
              <th class="p-3">납품처</th>
              <th class="p-3">상태</th>
              <th class="p-3">작업</th>
            </tr>
          </thead>

          <tbody>
            <template v-for="batch in purchaseBatches" :key="batch.key">
              <tr class="border-t bg-slate-50/70">
                <td class="p-3 font-semibold" colspan="9">
                  발주ID #{{ batch.batch_id }} · {{ batch.company }} ·
                  <span class="text-slate-500">발주시간 {{ formatOrderTime(batch.created_at) }}</span>
                </td>
              </tr>

              <template v-for="(o, idx) in batch.items" :key="o?.id ?? `${batch.batch_id}-${idx}`">
                <tr class="border-t">

                  <td class="p-3">{{ batch.batch_id }}</td>

                  <td class="p-3">
                    {{ o?.product_name || "-" }}
                    <div class="text-xs text-gray-400">
                      {{ o?.product_code || "-" }}
                    </div>
                  </td>

                  <td class="p-3">{{ o?.quantity ?? 0 }}</td>
                  <td class="p-3">{{ o?.received_quantity ?? 0 }}</td>
                  <td class="p-3">{{ (o?.quantity || 0) - (o?.received_quantity || 0) }}</td>
                  <td class="p-3">
                    {{
                      (receiptMap.get(receiptKey(o?.id)) || []).length
                        ? formatOrderTime((receiptMap.get(receiptKey(o?.id)) || []).slice(-1)[0].created_at)
                        : "-"
                    }}
                  </td>
                  <td class="p-3">{{ o?.company || "-" }}</td>

                  <td class="p-3">
                    <span v-if="o?.status === 'WAIT'">대기</span>
                    <span v-else-if="o?.status === 'PARTIAL'">부분입고</span>
                    <span v-else>완료</span>
                  </td>

                  <td class="p-3 flex gap-2">
                    <button v-if="o?.status === 'WAIT'"
                      @click="completePurchase(o.id)"
                      class="btn btn-success h-8 px-2 text-xs">
                      전체 입고
                    </button>

                    <button v-if="o?.status !== 'DONE'"
                      @click="partialPurchase(o)"
                      class="btn btn-secondary h-8 px-2 text-xs">
                      부분 입고
                    </button>

                    <button
                      @click="o?.id && toggleReceipt(o.id)"
                      class="btn btn-secondary h-8 px-2 text-xs">
                      {{ showReceipt[receiptKey(o?.id)] ? "입고내역 닫기" : "입고내역" }}
                    </button>

                    <button v-if="o?.status !== 'DONE'"
                      @click="deletePurchaseOrder(o.id)"
                      class="btn btn-danger h-8 px-2 text-xs">
                      삭제
                    </button>

                    <button v-if="o?.status === 'DONE'"
                      @click="undoPurchase(o.id)"
                      class="btn btn-secondary h-8 px-2 text-xs">
                      취소
                    </button>
                  </td>

                </tr>

                <tr v-if="o?.id && showReceipt[receiptKey(o.id)]" class="border-t bg-white">
                  <td colspan="9" class="p-3">
                    <div class="text-sm font-semibold mb-2">입고 내역</div>
                    <div v-if="!(receiptMap.get(receiptKey(o.id)) || []).length" class="text-xs text-slate-400">
                      입고 내역이 없습니다.
                    </div>
                    <div v-else class="flex flex-col gap-1">
                      <div v-for="r in (receiptMap.get(receiptKey(o.id)) || [])" :key="r.id"
                        class="text-sm text-slate-700 flex gap-3">
                        <span class="w-40">{{ formatOrderTime(r.created_at) }}</span>
                        <span>+{{ r.quantity }}</span>
                      </div>
                    </div>
                  </td>
                </tr>
              </template>
            </template>
          </tbody>

        </table>
      </div>

      <!-- 발주 등록 모달 -->
      <div v-if="showPurchaseModal" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/40" @click="showPurchaseModal = false"></div>
        <div class="relative bg-white w-[95vw] max-w-5xl max-h-[85vh] rounded-2xl shadow-xl overflow-hidden">
          <div class="flex items-center justify-between px-4 py-3 border-b">
            <div class="font-semibold">발주 등록</div>
            <div class="flex items-center gap-2">
              <button class="btn btn-secondary" @click="showPurchaseModal = false">닫기</button>
              <button class="btn btn-primary" @click="createPurchaseOrders">저장</button>
            </div>
          </div>
          <div class="p-4 flex flex-col gap-3 overflow-y-auto max-h-[75vh]">
            <div class="relative w-64">
              <input
                v-model="purchaseCompanyInput"
                @focus="showPurchaseCompanyDropdown = true"
                @blur="setTimeout(() => showPurchaseCompanyDropdown = false, 200)"
                placeholder="납품처"
                class="input w-full"
              />
              <div v-if="showPurchaseCompanyDropdown"
                class="absolute bg-white border w-full z-50 max-h-40 overflow-y-auto rounded-lg shadow">
                <div v-for="c in filteredPurchaseCompanies"
                  :key="c.id"
                  @click="selectPurchaseCompany(c)"
                  class="p-2 hover:bg-slate-100 cursor-pointer">
                  {{ c.name }}
                </div>
              </div>
            </div>

            <div class="grid grid-cols-[48px_220px_120px_1fr] gap-2 items-center text-xs text-slate-500">
              <div>#</div>
              <div>품번/품명</div>
              <div>수량</div>
              <div>제품명</div>
            </div>

            <div v-for="(row, idx) in purchaseRows" :key="idx" class="grid grid-cols-[48px_220px_120px_1fr] gap-2 items-center">
              <div class="text-xs text-slate-500">{{ idx + 1 }}</div>

              <div class="relative">
                <input
                  v-model="row.codeInput"
                  @focus="purchaseRowDropdown[idx] = true"
                  @blur="setTimeout(() => purchaseRowDropdown[idx] = false, 200)"
                  placeholder="품번/품명"
                  class="input w-full"
                />
                <div v-if="purchaseRowDropdown[idx]"
                  class="absolute bg-white border w-full z-50 max-h-40 overflow-y-auto rounded-lg shadow">
                  <div v-for="a in filteredPurchaseRowCodes(row)"
                    :key="a.key"
                    @click="selectPurchaseRowCode(idx, a.code)"
                    class="p-2 hover:bg-slate-100 cursor-pointer text-sm">
                    {{ a.label }}
                  </div>
                </div>
              </div>

              <input
                v-model="row.quantity"
                type="number"
                min="1"
                placeholder="수량"
                class="input w-full"
              />

              <div class="text-sm text-slate-700">
                {{ resolveProduct(row.selectedCode || row.codeInput)?.product?.name || "-" }}
              </div>
            </div>

            <div class="flex items-center justify-between pt-2">
              <button class="btn btn-secondary" @click="addPurchaseRow">
                줄 추가
              </button>
              <div class="text-xs text-slate-500">기본 10줄 제공</div>
            </div>
          </div>
        </div>
      </div>

    </div>

  </div>
</template>
