<script setup>
import { ref, onMounted, onUnmounted, computed } from "vue";
import api from "../api";

const orders = ref([]);
const purchaseOrders = ref([]);
const purchaseReceipts = ref([]);
const products = ref([]);
const companies = ref([]);
const boms = ref([]);
const inventory = ref([]);

const loadingAll = ref(false);
const loadError = ref("");

const activeTab = ref("incoming");

const companyInput = ref("");
const selectedCompany = ref("");

const codeInput = ref("");
const selectedCode = ref("");

const quantity = ref("");

// 발주 등록에서 납품처 입력은 제거 (발주서의 발주처는 단품의 발주처 기준으로 자동 입력)
const purchaseDueDate = ref(""); // YYYY-MM-DD
const showPurchaseModal = ref(false);
const purchaseRows = ref([]);
const purchaseRowDropdown = ref({});
const showEditPurchaseModal = ref(false);
const editPurchase = ref({
  id: null,
  company: "",
  codeInput: "",
  quantity: ""
});
const editPurchaseDropdown = ref(false);
const editingReceiptId = ref(null);
const editReceiptQty = ref("");
const editReceiptAt = ref("");

// 표시
const displayProduct = ref("");
const stockWarning = ref("");
const showCompleted = ref(false);
const showPurchaseCompleted = ref(false);

// 기간별 수주 합계 (생성일 기준)
const salesFromDate = ref(""); // YYYY-MM-DD
const salesToDate = ref("");   // YYYY-MM-DD

// 견적 이메일
const showQuoteModal = ref(false);
const quoteTo = ref("");
const quoteSubject = ref("");
const quoteBody = ref("");

// ⭐ 공통 문자열 정리 함수 (핵심)
const clean = (v) => (v || "").trim().toLowerCase();

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

const formatKstYmd = (dateValue) => {
  const date = parseUtcDate(dateValue);
  if (!date) return "";
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(date);
};

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
  loadingAll.value = true;
  loadError.value = "";

  const results = await Promise.allSettled([
    api.get("/orders/"),
    api.get("/purchase-orders/"),
    api.get("/purchase-orders/receipts"),
    api.get("/products/"),
    api.get("/companies/"),
    api.get("/bom/"),
    api.get("/inventory/"),
  ]);

  const [o, po, pr, p, c, b, i] = results;

  const errors = [];

  if (o.status === "fulfilled") {
    orders.value = o.value.data;
  } else {
    errors.push("수주");
  }

  if (po.status === "fulfilled") {
    purchaseOrders.value = po.value.data;
  } else {
    errors.push("발주");
  }

  if (pr.status === "fulfilled") {
    purchaseReceipts.value = pr.value.data;
  } else {
    errors.push("입고이력");
  }

  if (p.status === "fulfilled") {
    products.value = p.value.data.map((item) => ({
      ...item,
      code: item.new_code || item.code || "",
      old_code: item.old_code || ""
    }));
  } else {
    errors.push("제품");
  }

  if (c.status === "fulfilled") {
    companies.value = c.value.data;
  } else {
    errors.push("업체");
  }

  if (b.status === "fulfilled") {
    boms.value = b.value.data;
  } else {
    errors.push("BOM");
  }

  if (i.status === "fulfilled") {
    inventory.value = i.value.data;
  } else {
    errors.push("재고");
  }

  if (errors.length) {
    loadError.value = `데이터 로드 실패: ${errors.join(", ")} (네트워크/서버 상태를 확인해줘)`;
  }

  loadingAll.value = false;
};

const closeAllDropdowns = () => {
  showCompanyDropdown.value = false;
  showCodeDropdown.value = false;
  editPurchaseDropdown.value = false;
  purchaseRowDropdown.value = {};
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

// (구) 납품처 자동완성 드롭다운 제거

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

// (구) 납품처 선택 제거

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

const addPurchaseRows = (count) => {
  const n = Number(count);
  if (!Number.isFinite(n) || n <= 0) return;
  for (let i = 0; i < n; i += 1) {
    purchaseRows.value.push({
      codeInput: "",
      selectedCode: "",
      quantity: ""
    });
  }
};

const addPurchaseRowsPrompt = () => {
  const input = window.prompt("몇 줄 추가할까요?", "1");
  if (!input) return;
  addPurchaseRows(Number(input));
};

const filteredPurchaseRowCodes = (row) => buildCodeOptions(row.codeInput);

const selectPurchaseRowCode = (index, code) => {
  const row = purchaseRows.value[index];
  if (!row) return;
  row.selectedCode = code;
  row.codeInput = code;
  purchaseRowDropdown.value[index] = false;
};

const openEditPurchase = (order) => {
  editPurchase.value = {
    id: order.id,
    company: order.company || "",
    codeInput: order.product_code || "",
    quantity: order.quantity || ""
  };
  showEditPurchaseModal.value = true;
};

const saveEditPurchase = async () => {
  const payload = {};
  const company = (editPurchase.value.company || "").trim();
  const code = (editPurchase.value.codeInput || "").trim();
  const qtyRaw = editPurchase.value.quantity;

  if (company) payload.company = company;
  if (code) payload.product_code = code;
  if (qtyRaw !== "" && qtyRaw !== null && qtyRaw !== undefined) {
    payload.quantity = Number(qtyRaw);
  }

  try {
    await api.put(`/purchase-orders/${editPurchase.value.id}`, payload);
    showEditPurchaseModal.value = false;
    await loadAll();
  } catch (err) {
    alert("수정 실패");
  }
};

const openEditReceipt = (receipt) => {
  editingReceiptId.value = receipt.id;
  editReceiptQty.value = receipt.quantity;
  const date = new Date(receipt.created_at);
  if (!Number.isNaN(date.getTime())) {
    const pad = (n) => String(n).padStart(2, "0");
    editReceiptAt.value = `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
  } else {
    editReceiptAt.value = "";
  }
};

const cancelEditReceipt = () => {
  editingReceiptId.value = null;
  editReceiptQty.value = "";
  editReceiptAt.value = "";
};

const saveEditReceipt = async () => {
  await api.put(`/purchase-orders/receipts/${editingReceiptId.value}`, {
    quantity: Number(editReceiptQty.value),
    created_at: editReceiptAt.value || null
  });
  cancelEditReceipt();
  await loadAll();
};

const deleteReceipt = async (id) => {
  const ok = window.confirm("입고 내역을 삭제할까요?");
  if (!ok) return;
  await api.delete(`/purchase-orders/receipts/${id}`);
  await loadAll();
};

// =====================
// 주문 생성
// =====================
const createOrder = async () => {
  const companyName = selectedCompany.value || companyInput.value;
  if (!companyName || !quantity.value) return alert("회사/수량을 입력하세요.");

  if (stockWarning.value) {
    const ok = window.confirm(
      "재고가 부족해 보입니다.\n그래도 수주를 등록할까요?\n(생산 버튼에서 재고 부족 시 막힙니다)"
    );
    if (!ok) return;
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
    });
  }

  if (payloads.length === 0) {
    return alert("입력된 발주 항목이 없습니다.");
  }

  const batchRes = await api.post("/purchase-orders/batch", {
    due_date: (purchaseDueDate.value || "").trim() || null,
    items: payloads.map((payload) => ({
      product_code: payload.product_code,
      quantity: payload.quantity
    }))
  });

  const batchId = batchRes?.data?.batch_id;
  if (batchId) {
    try {
      await downloadPurchaseBatchXlsx(batchId);
    } catch (err) {
      const retry = window.confirm(
        "발주 등록은 됐는데, 브라우저에서 자동 다운로드가 막힌 것 같습니다.\n지금 다운로드를 다시 시도할까요?"
      );
      if (retry) {
        try {
          await downloadPurchaseBatchXlsx(batchId);
        } catch (err2) {
          alert("엑셀 다운로드에 실패했습니다. (네트워크/권한/팝업 설정 확인)");
        }
      }
    }
  }

  showPurchaseModal.value = false;
  initPurchaseRows();
  purchaseDueDate.value = "";
  loadAll();
};

const downloadPurchaseBatchXlsx = async (batchId) => {
  if (!batchId) throw new Error("missing_batch_id");

  const fileRes = await api.get(`/purchase-orders/batch/${batchId}/xlsx`, {
    responseType: "blob"
  });

  const blob = fileRes.data instanceof Blob
    ? fileRes.data
    : new Blob([fileRes.data], {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    });

  const contentType = String(fileRes?.headers?.["content-type"] || blob.type || "");
  if (contentType.includes("application/json")) {
    const text = await blob.text();
    throw new Error(text || "download_failed");
  }

  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  const disposition = fileRes?.headers?.["content-disposition"] || "";
  const match = disposition.match(/filename\\*=UTF-8''([^;]+)|filename=\"?([^\";]+)\"?/i);
  const filename = match?.[1]
    ? decodeURIComponent(match[1])
    : (match?.[2] || `purchase_order_${batchId}.xlsx`);

  a.download = filename;
  a.href = url;
  a.style.display = "none";
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.setTimeout(() => window.URL.revokeObjectURL(url), 1500);
};

const onClickDownloadPurchaseBatchXlsx = async (batchId) => {
  try {
    await downloadPurchaseBatchXlsx(batchId);
  } catch (err) {
    alert("엑셀 다운로드에 실패했습니다. (네트워크/권한/팝업 설정 확인)");
  }
};

const onClickDownloadSalesSummaryXlsx = async () => {
  try {
    const params = new URLSearchParams();
    if ((salesFromDate.value || "").trim()) params.set("from", salesFromDate.value.trim());
    if ((salesToDate.value || "").trim()) params.set("to", salesToDate.value.trim());
    const qs = params.toString();

    const fileRes = await api.get(`/orders/summary-xlsx${qs ? `?${qs}` : ""}`, {
      responseType: "blob"
    });

    const blob = fileRes.data instanceof Blob
      ? fileRes.data
      : new Blob([fileRes.data], {
        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
      });

    const contentType = String(fileRes?.headers?.["content-type"] || blob.type || "");
    if (contentType.includes("application/json")) {
      const text = await blob.text();
      throw new Error(text || "download_failed");
    }

    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    const disposition = fileRes?.headers?.["content-disposition"] || "";
    const match = disposition.match(/filename\\*=UTF-8''([^;]+)|filename=\"?([^\";]+)\"?/i);
    const filename = match?.[1]
      ? decodeURIComponent(match[1])
      : (match?.[2] || "sales_summary.xlsx");

    a.download = filename;
    a.href = url;
    a.style.display = "none";
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.setTimeout(() => window.URL.revokeObjectURL(url), 1500);
  } catch (err) {
    alert("엑셀 다운로드에 실패했습니다. (네트워크/권한/팝업 설정 확인)");
  }
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
  try {
    await api.post(`/purchase-orders/undo/${id}`);
    showPurchaseCompleted.value = false;
    await loadAll();
    alert("취소 완료: 대기목록으로 이동했습니다.");
  } catch (err) {
    alert("취소 실패");
  }
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

const handleGlobalClick = () => closeAllDropdowns();

onMounted(() => {
  loadAll();
  window.addEventListener("click", handleGlobalClick);
});

onUnmounted(() => {
  window.removeEventListener("click", handleGlobalClick);
});

const pendingOrders = computed(() =>
  orders.value.filter((o) => o.status === "WAIT")
);

const completedOrders = computed(() =>
  orders.value.filter((o) => o.status === "DONE")
);

const visibleOrders = computed(() =>
  showCompleted.value ? completedOrders.value : pendingOrders.value
);

const ordersInSalesRange = computed(() => {
  const from = (salesFromDate.value || "").trim();
  const to = (salesToDate.value || "").trim();
  if (!from && !to) return orders.value;

  return orders.value.filter((o) => {
    const ymd = formatKstYmd(o?.created_at);
    if (!ymd) return false;
    if (from && ymd < from) return false;
    if (to && ymd > to) return false;
    return true;
  });
});

const salesSummaryRows = computed(() => {
  const map = new Map();

  for (const o of ordersInSalesRange.value) {
    if (!o || typeof o !== "object") continue;
    const newCode = (o.new_code || o.product_code || "").toString();
    if (!newCode) continue;
    const key = newCode.toLowerCase();

    if (!map.has(key)) {
      map.set(key, {
        old_code: (o.old_code || "").toString(),
        new_code: newCode,
        product_name: (o.product_name || "").toString(),
        quantity: 0,
      });
    }

    map.get(key).quantity += Number(o.quantity || 0);
  }

  return Array.from(map.values()).sort((a, b) =>
    String(a.new_code || "").localeCompare(String(b.new_code || ""))
  );
});

const totalSalesQty = computed(() =>
  salesSummaryRows.value.reduce((sum, r) => sum + Number(r.quantity || 0), 0)
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
        title: o.batch_title || "",
        created_at: o.batch_created_at || o.created_at,
        status: o.batch_status || o.status,
        items: []
      });
    }
    map.get(key).items.push(o);
  }

  return Array.from(map.values()).sort((a, b) => (b.batch_id || 0) - (a.batch_id || 0));
});

const getPurchaseBatchTitle = (batch) => {
  return (batch?.title || "").trim() || "단품";
};


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

const formatOrderDate = (dateValue) => {
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
    day: "2-digit"
  }).format(date);
};

const formatBatchId = (dateValue, seq) => {
  if (!dateValue) return "-";
  const raw = String(dateValue).trim();
  const normalized = raw.includes("T") ? raw : raw.replace(" ", "T");
  const withTimezone = /[zZ]|[+\-]\d{2}:\d{2}$/.test(normalized)
    ? normalized
    : `${normalized}Z`;
  const date = new Date(withTimezone);
  if (Number.isNaN(date.getTime())) return "-";
  const yy = String(date.getFullYear()).slice(-2);
  const mm = String(date.getMonth() + 1).padStart(2, "0");
  const dd = String(date.getDate()).padStart(2, "0");
  return `${yy}-${mm}-${dd}-${seq}`;
};

const purchaseBatchIdMap = computed(() => {
  const list = [...purchaseBatches.value].sort((a, b) => {
    const ta = new Date(a.created_at).getTime();
    const tb = new Date(b.created_at).getTime();
    if (Number.isNaN(ta) || Number.isNaN(tb)) return 0;
    return ta - tb;
  });

  const counter = new Map();
  const map = new Map();

  for (const batch of list) {
    const dateKey = formatOrderDate(batch.created_at);
    const current = (counter.get(dateKey) || 0) + 1;
    counter.set(dateKey, current);
    map.set(batchKey(batch), formatBatchId(batch.created_at, current));
  }

  return map;
});

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

const showBatch = ref({});
const batchKey = (batch) => String(batch?.key ?? batch?.batch_id ?? "");
const toggleBatch = (batch) => {
  const key = batchKey(batch);
  showBatch.value = {
    ...showBatch.value,
    [key]: !showBatch.value[key]
  };
};

const deleteOrder = async (id) => {
  const ok = window.confirm("\uC218\uC8FC\uB97C \uC0AD\uC81C(\uAC70\uBD80)\uD560\uAE4C\uC694?");
  if (!ok) return;
  await api.delete(`/orders/${id}`);
  loadAll();
};

const deletePurchaseOrder = async (id) => {
  const ok = window.confirm("발주를 삭제할까요?");
  if (!ok) return;
  try {
    await api.delete(`/purchase-orders/${id}`);
    await loadAll();
  } catch (err) {
    alert("삭제 실패");
  }
};

const deletePurchaseBatch = async (batchId) => {
  if (!batchId) return;
  const ok = window.confirm(
    "이 발주서(배치)를 통째로 삭제할까요?\n(하위 발주 항목/입고 기록도 함께 삭제됩니다)"
  );
  if (!ok) return;

  try {
    await api.delete(`/purchase-orders/batch/${batchId}`);
    await loadAll();
  } catch (err) {
    alert("발주서 삭제 실패");
  }
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
        &#xC218;&#xC8FC;
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
        <h2 class="page-title">📋 &#xC218;&#xC8FC; &#xAD00;&#xB9AC;</h2>
        <button
          @click="showCompleted = !showCompleted"
          class="btn btn-secondary"
        >
          {{ showCompleted ? "대기목록 보기" : "완료내역 보기" }}
        </button>
      </div>

    <!-- 기간별 수주 합계 (생성일 기준) -->
    <div class="panel p-3 mb-6">
      <div class="panel-header flex items-center justify-between">
        <span>기간별 수주 합계</span>
        <div class="flex items-center gap-2">
          <span class="text-xs text-slate-500">총 {{ totalSalesQty }}개</span>
          <button
            class="btn btn-secondary h-8 px-2 text-xs"
            @click="onClickDownloadSalesSummaryXlsx"
          >
            엑셀 저장
          </button>
        </div>
      </div>
      <div class="p-3 flex flex-col gap-3">
        <div class="flex flex-wrap gap-2 items-center">
          <input v-model="salesFromDate" type="date" class="input w-44" aria-label="시작일" />
          <span class="text-slate-400">~</span>
          <input v-model="salesToDate" type="date" class="input w-44" aria-label="종료일" />
          <button class="btn btn-secondary" @click="salesFromDate=''; salesToDate=''">초기화</button>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-left text-sm">
            <thead class="bg-slate-100 text-slate-600">
              <tr>
                <th class="p-2">구품번</th>
                <th class="p-2">신품번</th>
                <th class="p-2">제품명</th>
                <th class="p-2 text-right">수량</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in salesSummaryRows" :key="`sales-${row.new_code}`" class="border-t">
                <td class="p-2 font-medium">{{ row.old_code || "-" }}</td>
                <td class="p-2">{{ row.new_code || "-" }}</td>
                <td class="p-2">{{ row.product_name || "-" }}</td>
                <td class="p-2 text-right font-semibold">{{ row.quantity }}</td>
              </tr>
              <tr v-if="salesSummaryRows.length === 0">
                <td class="p-3 text-center text-slate-400" colspan="4">해당 기간 수주가 없습니다.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div class="panel p-3 mb-6 flex gap-3 items-center flex-wrap overflow-visible">

      <div class="relative w-40" @click.stop>
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

      <div class="relative w-40" @click.stop>
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
        &#xC218;&#xC8FC; &#xC0DD;&#xC131;
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

    <div class="panel overflow-x-auto">
      <table class="w-full text-left table-nowrap">

        <thead class="table-head">
          <tr>
            <th class="p-3">구품번</th>
            <th class="p-3">신품번</th>
            <th class="p-3">수량</th>
            <th class="p-3">업체</th>
            <th class="p-3">상태</th>
            <th class="p-3">작업</th>
          </tr>
        </thead>

        <tbody>
          <tr v-for="o in visibleOrders" :key="o.id" class="border-t">

            <td class="p-3 font-medium">{{ o.old_code || "-" }}</td>
            <td class="p-3">{{ o.new_code || o.product_code || "-" }}</td>

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

      <div v-if="loadError" class="mb-4 p-3 rounded-xl border border-rose-200 bg-rose-50 text-rose-700 text-sm">
        {{ loadError }}
      </div>
      <div v-else-if="loadingAll" class="mb-4 p-3 rounded-xl border border-slate-200 bg-slate-50 text-slate-600 text-sm">
        로딩 중...
      </div>

      <div class="panel overflow-x-auto">
        <table class="w-full text-left table-nowrap">

          <tbody>
            <tr v-if="!purchaseBatches.length">
              <td class="p-4 text-sm text-slate-500" colspan="8">
                발주 내역이 없습니다.
                <span v-if="purchaseOrders.length && !showPurchaseCompleted && !pendingPurchaseOrders.length && completedPurchaseOrders.length">
                  (현재 대기 발주가 없어요. 상단의 "완료내역 보기"를 눌러보세요.)
                </span>
              </td>
            </tr>
            <template v-for="batch in purchaseBatches" :key="batch.key">
              <tr class="border-t bg-slate-50/70">
                <td class="p-3 font-semibold" colspan="8">
                  <div class="flex items-center justify-between gap-3">
                    <div>
                      <span class="text-slate-500">{{ formatOrderDate(batch.created_at) }}</span>
                      · {{ getPurchaseBatchTitle(batch) }}
                    </div>
                    <div class="flex items-center gap-2">
                      <button
                        class="btn btn-primary h-8 px-2 text-xs"
                        @click="onClickDownloadPurchaseBatchXlsx(batch.batch_id)"
                      >
                        엑셀 저장
                      </button>
                      <button
                        class="btn btn-secondary h-8 px-2 text-xs"
                        @click="deletePurchaseBatch(batch.batch_id)"
                      >
                        삭제
                      </button>
                      <button class="btn btn-secondary h-8 px-2 text-xs" @click="toggleBatch(batch)">
                        {{ showBatch[batchKey(batch)] ? "접기" : "자세히보기" }}
                      </button>
                    </div>
                  </div>
                </td>
              </tr>

              <template v-if="showBatch[batchKey(batch)]">
                <tr class="table-head">
                  <th class="p-3">제품</th>
                  <th class="p-3">주문수량</th>
                  <th class="p-3">입고수량</th>
                  <th class="p-3">잔여</th>
                  <th class="p-3">최근 입고</th>
                  <th class="p-3">납품처</th>
                  <th class="p-3">상태</th>
                  <th class="p-3">작업</th>
                </tr>

                <template v-for="(o, idx) in batch.items" :key="o?.id ?? `${batch.batch_id}-${idx}`">
                <tr class="border-t">

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

                  <button
                    @click="openEditPurchase(o)"
                    class="btn btn-secondary h-8 px-2 text-xs">
                    수정
                  </button>

                  <button v-if="o?.status === 'DONE'"
                    @click="undoPurchase(o.id)"
                    class="btn btn-secondary h-8 px-2 text-xs">
                    취소
                  </button>
                </td>

                </tr>

                <tr v-if="o?.id && showReceipt[receiptKey(o.id)]" class="border-t bg-white">
                  <td colspan="8" class="p-3">
                    <div class="text-sm font-semibold mb-2">입고 내역</div>
                    <div v-if="!(receiptMap.get(receiptKey(o.id)) || []).length" class="text-xs text-slate-400">
                      입고 내역이 없습니다.
                    </div>
                    <div v-else class="flex flex-col gap-1">
                      <div v-for="r in (receiptMap.get(receiptKey(o.id)) || [])" :key="r.id"
                        class="text-sm text-slate-700 flex gap-3 items-center">
                        <span class="w-40">{{ formatOrderTime(r.created_at) }}</span>
                        <span>+{{ r.quantity }}</span>
                        <button class="btn btn-secondary h-7 px-2 text-xs" @click="openEditReceipt(r)">
                          수정
                        </button>
                        <button class="btn btn-danger h-7 px-2 text-xs" @click="deleteReceipt(r.id)">
                          삭제
                        </button>
                      </div>
                    </div>
                  </td>
                </tr>
                </template>
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
            <div class="flex flex-wrap gap-3 items-start">
              <div class="w-48">
                <input
                  v-model="purchaseDueDate"
                  type="date"
                  class="input w-full"
                  aria-label="납기일"
                  title="납기일 (YYYY-MM-DD)"
                />
              </div>
              <div class="text-xs text-slate-500 self-center">
                납기일 (연-월-일)
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

              <div class="relative" @click.stop>
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
            <button class="btn btn-secondary" @click="addPurchaseRowsPrompt">
              줄 추가
            </button>
            <div class="text-xs text-slate-500">기본 10줄 제공</div>
          </div>
          </div>
        </div>
      </div>

      <!-- 발주 수정 모달 -->
      <div v-if="showEditPurchaseModal" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/40" @click="showEditPurchaseModal = false"></div>
        <div class="relative bg-white w-[90vw] max-w-xl rounded-2xl shadow-xl overflow-hidden">
          <div class="flex items-center justify-between px-4 py-3 border-b">
            <div class="font-semibold">발주 수정</div>
            <div class="flex items-center gap-2">
              <button class="btn btn-secondary" @click="showEditPurchaseModal = false">닫기</button>
              <button class="btn btn-primary" @click="saveEditPurchase">저장</button>
            </div>
          </div>
          <div class="p-4 flex flex-col gap-3">
            <input v-model="editPurchase.company" class="input w-full" placeholder="납품처" />

            <div class="relative" @click.stop>
              <input
                v-model="editPurchase.codeInput"
                @input="editPurchaseDropdown = true"
                @focus="editPurchaseDropdown = true"
                @blur="setTimeout(() => editPurchaseDropdown = false, 200)"
                placeholder="품번/품명"
                class="input w-full"
              />
              <div v-if="editPurchaseDropdown"
                class="absolute bg-white border w-full z-50 max-h-40 overflow-y-auto rounded-lg shadow">
                <div v-for="a in buildCodeOptions(editPurchase.codeInput)"
                  :key="a.key"
                  @mousedown.prevent
                  @click="editPurchase.codeInput = a.code; editPurchaseDropdown = false"
                  class="p-2 hover:bg-slate-100 cursor-pointer">
                  {{ a.label }}
                </div>
              </div>
            </div>

            <input v-model="editPurchase.quantity" type="number" min="1" class="input w-full" placeholder="수량" />
          </div>
        </div>
      </div>

      <!-- 입고 내역 수정 모달 -->
      <div v-if="editingReceiptId" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/40" @click="cancelEditReceipt"></div>
        <div class="relative bg-white w-[90vw] max-w-md rounded-2xl shadow-xl overflow-hidden">
          <div class="flex items-center justify-between px-4 py-3 border-b">
            <div class="font-semibold">입고 내역 수정</div>
            <div class="flex items-center gap-2">
              <button class="btn btn-secondary" @click="cancelEditReceipt">닫기</button>
              <button class="btn btn-primary" @click="saveEditReceipt">저장</button>
            </div>
          </div>
          <div class="p-4 flex flex-col gap-3">
            <input v-model="editReceiptQty" type="number" min="1" class="input w-full" placeholder="수량" />
            <input v-model="editReceiptAt" type="datetime-local" class="input w-full" />
          </div>
        </div>
      </div>

    </div>

  </div>
</template>
