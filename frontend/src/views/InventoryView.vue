<script setup>
import { ref, onMounted, onUnmounted, computed, watch } from "vue";
import api from "../api";
import * as XLSX from "xlsx";
import factoryLayoutUrl from "../assets/factory_layout.png";
import factoryLocationBoxes from "../assets/factory_location_boxes.json";

const inventory = ref([]);
const products = ref([]);
const companies = ref([]);
const searchCode = ref("");
const searchNameInput = ref("");
const showNameDropdown = ref(false);
const typeFilter = ref("PART");
const showAllPartsModal = ref(false);
const showPartsManageModal = ref(false);
const partsModalTab = ref("register");
const showLocationMapModal = ref(false);
const mapLocationCode = ref("");
const mapZoom = ref(1);
const mapEditMode = ref(false);
const mapPendingPoint = ref(null); // { x: number, y: number } in %
const mapHighlightTone = ref("warn"); // warn | danger
const mapImageUrl = ref("");
const mapImageLoading = ref(false);
const mapImageError = ref("");
const mapImageObjectUrl = ref("");

// 입고
const stockInCode = ref("");
const stockInNameInput = ref("");
const stockInQuantity = ref("");
const stockInReason = ref("입고");
const showStockInCodeDropdown = ref(false);
const showStockInNameDropdown = ref(false);

const code = ref("");
const nameInput = ref("");
const quantity = ref("");
const showAddNameDropdown = ref(false);
const showAddCodeDropdown = ref(false);
const oldCodeInput = ref("");
const drawingNumberInput = ref("");
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
const editDrawingNumber = ref("");
const editNewCode = ref("");
const editMaterial = ref("");
const editSpec = ref("");
const editHeatTreatment = ref("");
const editWelding = ref("");
const editPlating = ref("");
const editLocation = ref("");
const editMinStock = ref("");
const editQuantity = ref("");
const editReason = ref("");
const editReasonPreset = ref("");
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

const normalizeLocationCode = (value) => {
  const raw = (value || "").toString().trim().toUpperCase();
  if (!raw) return "";

  // Accept both "A-1" and "A-01" forms (pad to 2 digits).
  const m = raw.match(/^([A-Z])\s*-\s*([0-9]{1,2})$/);
  if (m) {
    return `${m[1]}-${String(m[2]).padStart(2, "0")}`;
  }

  // Fallback: remove extra spaces only.
  return raw.replace(/\s+/g, "");
};

// 배치도 좌표는 이미지 기준 비율(%)로 저장해서 화면 크기가 달라도 위치가 맞게 한다.
// 필요하면 나중에 "좌표 편집 모드"로 정확도를 더 올릴 수 있음.
// v4: factory_layout.png rendered from Excel source (canonical labels like A-01).
const LOCATION_STORAGE_KEY = "factoryLocationPoints.v4";
const DEFAULT_LOCATION_POINTS = {};

const loadSavedLocationPoints = () => {
  try {
    if (typeof window === "undefined") return null;
    const raw = window.localStorage.getItem(LOCATION_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return null;
    return parsed;
  } catch {
    return null;
  }
};

const saveLocationPoints = (points) => {
  try {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(LOCATION_STORAGE_KEY, JSON.stringify(points));
  } catch {
    // ignore
  }
};

const locationPoints = ref({
  ...DEFAULT_LOCATION_POINTS,
  ...(loadSavedLocationPoints() || {})
});

const setLocationPoint = (code, point) => {
  const key = normalizeLocationCode(code);
  if (!key || !point) return;
  const next = {
    ...locationPoints.value,
    [key]: { x: Number(point.x), y: Number(point.y) }
  };
  locationPoints.value = next;
  saveLocationPoints(next);
};

const saveBlobAsFile = (blob, filename) => {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

const readDownloadError = async (err) => {
  const data = err?.response?.data;
  if (data instanceof Blob) {
    try {
      const text = await data.text();
      const parsed = JSON.parse(text);
      return parsed.detail || text;
    } catch {
      return "";
    }
  }
  return data?.detail || "";
};

const clearMapImageUrl = () => {
  if (mapImageObjectUrl.value) {
    window.URL.revokeObjectURL(mapImageObjectUrl.value);
  }
  mapImageObjectUrl.value = "";
  mapImageUrl.value = "";
};

const loadLocationMapImage = async (code, danger) => {
  clearMapImageUrl();
  mapImageLoading.value = true;
  mapImageError.value = "";

  try {
    const res = await api.get(`/inventory/location-map-image/${encodeURIComponent(code)}`, {
      params: { danger },
      responseType: "blob"
    });
    const url = window.URL.createObjectURL(res.data);
    mapImageObjectUrl.value = url;
    mapImageUrl.value = url;
  } catch (err) {
    const detail = await readDownloadError(err);
    mapImageError.value = detail || `${code} 위치가 표시된 배치도 이미지를 만들지 못했습니다.`;
  } finally {
    mapImageLoading.value = false;
  }
};

const openLocationMap = async (locationCode, meta = null) => {
  const code = normalizeLocationCode(locationCode);
  if (!code) return;

  const qty = meta && meta.quantity !== undefined ? Number(meta.quantity) : NaN;
  const min = meta && meta.min_stock !== undefined ? Number(meta.min_stock) : NaN;
  const danger = Number.isFinite(qty) && Number.isFinite(min) && qty <= min;

  mapLocationCode.value = code;
  mapZoom.value = 1;
  mapEditMode.value = false;
  mapPendingPoint.value = null;
  mapHighlightTone.value = danger ? "danger" : "warn";
  showLocationMapModal.value = true;
  await loadLocationMapImage(code, danger);
};

const downloadLocationMapExcel = async () => {
  const code = normalizeLocationCode(mapLocationCode.value);
  if (!code) return;
  const danger = mapHighlightTone.value === "danger";

  try {
    const res = await api.get(`/inventory/location-map/${encodeURIComponent(code)}`, {
      params: { danger },
      responseType: "blob"
    });
    saveBlobAsFile(res.data, `factory_layout_${code}.xlsx`);
  } catch (err) {
    const detail = await readDownloadError(err);
    alert(detail || `${code} 위치가 표시된 배치도 엑셀을 만들지 못했습니다.`);
  }
};

const closeLocationMap = () => {
  showLocationMapModal.value = false;
  mapLocationCode.value = "";
  mapZoom.value = 1;
  mapEditMode.value = false;
  mapPendingPoint.value = null;
  mapImageLoading.value = false;
  mapImageError.value = "";
  clearMapImageUrl();
};

const activeLocationPoint = computed(() => {
  const code = normalizeLocationCode(mapLocationCode.value);
  return locationPoints.value[code] || null;
});

const activeLocationBox = computed(() => {
  const code = normalizeLocationCode(mapLocationCode.value);
  return factoryLocationBoxes?.[code] || null;
});

// Render calibration: use the detected cell center, then fill inward from it.
const BOX_ADJUST = { centerDxByW: 0.2, centerDyByH: 0.52, scaleW: 0.72, scaleH: 0.68 };
const adjustedLocationBox = computed(() => {
  const b = activeLocationBox.value;
  if (!b) return null;
  const x = Number(b.x) || 0;
  const y = Number(b.y) || 0;
  const w = Number(b.w) || 0;
  const h = Number(b.h) || 0;
  return {
    cx: clamp(x + w / 2 + w * BOX_ADJUST.centerDxByW, 0, 100),
    cy: clamp(y + h / 2 + h * BOX_ADJUST.centerDyByH, 0, 100),
    w: clamp(w * BOX_ADJUST.scaleW, 0, 100),
    h: clamp(h * BOX_ADJUST.scaleH, 0, 100)
  };
});

const displayLocationPoint = computed(() => {
  return mapPendingPoint.value || activeLocationPoint.value || null;
});

const mapHighlightClass = computed(() => {
  return mapHighlightTone.value === "danger"
    ? "bg-red-500/40"
    : "bg-yellow-300/50";
});

const clamp = (v, min, max) => Math.max(min, Math.min(max, v));
const zoomInMap = () => {
  mapZoom.value = clamp(Number(mapZoom.value || 1) + 0.1, 0.6, 2.6);
};
const zoomOutMap = () => {
  mapZoom.value = clamp(Number(mapZoom.value || 1) - 0.1, 0.6, 2.6);
};
const resetMapZoom = () => {
  mapZoom.value = 1;
};

const toggleMapEditMode = () => {
  mapEditMode.value = !mapEditMode.value;
  mapPendingPoint.value = null;
};

const onMapClick = (event) => {
  if (!mapEditMode.value) return;
  const code = normalizeLocationCode(mapLocationCode.value);
  if (!code) return;

  const target = event?.currentTarget;
  if (!target || typeof target.getBoundingClientRect !== "function") return;

  const rect = target.getBoundingClientRect();
  const x = ((event.clientX - rect.left) / rect.width) * 100;
  const y = ((event.clientY - rect.top) / rect.height) * 100;

  if (!Number.isFinite(x) || !Number.isFinite(y)) return;
  mapPendingPoint.value = {
    x: clamp(x, 0, 100),
    y: clamp(y, 0, 100)
  };
};

const savePendingPoint = () => {
  const code = normalizeLocationCode(mapLocationCode.value);
  if (!code || !mapPendingPoint.value) return;
  setLocationPoint(code, mapPendingPoint.value);
  mapEditMode.value = false;
  mapPendingPoint.value = null;
};

// =====================
// 데이터 로드
// =====================
const loadInventory = async () => {
  const res = await api.get("/inventory/");
  inventory.value = res.data.map((item) => ({
    ...item,
    new_code: item.new_code || item.code || "",
    old_code: item.old_code || "",
    drawing_number: item.drawing_number || "",
    name: item.name || "",
    material: item.material || "",
    spec: item.spec || "",
    location: normalizeLocationCode(item.location || ""),
    type: (item.type || "PART").toString().toUpperCase()
  }));
};

const closeAllDropdowns = () => {
  showNameDropdown.value = false;
  showStockInCodeDropdown.value = false;
  showStockInNameDropdown.value = false;
  showAddNameDropdown.value = false;
  showAddCodeDropdown.value = false;
  showSupplierDropdown.value = false;
};

const loadProducts = async () => {
  const res = await api.get("/products/");
  products.value = res.data.map((item) => ({
    ...item,
    code: item.new_code || item.code || "",
    drawing_number: item.drawing_number || "",
    old_code: item.old_code || "",
    location: normalizeLocationCode(item.location || "")
  }));
};

const findPartByCodeOrName = (codeValue, nameValue) => {
  const codeKeyword = (codeValue || "").trim().toLowerCase();
  const nameKeyword = (nameValue || "").trim().toLowerCase();
  return inventory.value.find((item) => {
    if ((item.type || "PART").toString().toUpperCase() !== "PART") return false;
    const newCode = (item.new_code || item.code || "").toLowerCase();
    const oldCode = (item.old_code || "").toLowerCase();
    const name = (item.name || "").toLowerCase();
    return (
      (codeKeyword && (newCode === codeKeyword || oldCode === codeKeyword)) ||
      (!codeKeyword && nameKeyword && name === nameKeyword)
    );
  });
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
  const locationValue = normalizeLocationCode(locationInput.value);
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
      drawing_number: drawingNumberInput.value.trim(),
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
  drawingNumberInput.value = "";
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

const stockIn = async () => {
  const addQty = Number(stockInQuantity.value || 0);
  if (addQty <= 0) return alert("입고 수량을 입력하세요.");

  const matched = findPartByCodeOrName(stockInCode.value, stockInNameInput.value);
  if (!matched) {
    alert("입고할 단품을 찾을 수 없습니다. 품번 또는 품명을 확인해 주세요.");
    return;
  }

  const productCode = matched.new_code || matched.code;
  const currentQty = Number(matched.quantity || 0);
  const newQty = currentQty + addQty;

  await api.put(`/inventory/${productCode}`, {
    quantity: newQty,
    reason: stockInReason.value || "입고"
  });

  stockInCode.value = "";
  stockInNameInput.value = "";
  stockInQuantity.value = "";
  stockInReason.value = "입고";

  await loadInventory();
};

// =====================
// 재고 수정/삭제
// =====================
const startEdit = (item) => {
  editingCode.value = item.new_code || item.code || "";
  editName.value = item.name || "";
  editOldCode.value = item.old_code || "";
  editDrawingNumber.value = item.drawing_number || "";
  editNewCode.value = item.new_code || item.code || "";
  editMaterial.value = item.material || "";
  editSpec.value = item.spec || "";
  editHeatTreatment.value = item.heat_treatment || "";
  editWelding.value = item.welding || "";
  editPlating.value = item.plating || "";
  editLocation.value = item.location || "";
  editMinStock.value = String(item.min_stock ?? "");
  editQuantity.value = String(item.quantity ?? "");
  editReasonPreset.value = "";
  editSupplierCompanyId.value = item.supplier_company_id
    ? String(item.supplier_company_id)
    : "";
  editReason.value = "";
};

const cancelEdit = () => {
  editingCode.value = "";
  editName.value = "";
  editOldCode.value = "";
  editDrawingNumber.value = "";
  editNewCode.value = "";
  editMaterial.value = "";
  editSpec.value = "";
  editHeatTreatment.value = "";
  editWelding.value = "";
  editPlating.value = "";
  editLocation.value = "";
  editMinStock.value = "";
  editQuantity.value = "";
  editReasonPreset.value = "";
  editSupplierCompanyId.value = "";
  editReason.value = "";
};

const saveEdit = async () => {
  if (!editingCode.value) return;

  await api.put(`/products/${editingCode.value}`, {
    old_code: editOldCode.value,
    drawing_number: editDrawingNumber.value,
    name: editName.value,
    material: editMaterial.value,
    spec: editSpec.value,
    heat_treatment: editHeatTreatment.value,
    welding: editWelding.value,
    plating: editPlating.value,
    location: normalizeLocationCode(editLocation.value),
    min_stock: Number(editMinStock.value || 0),
    supplier_company_id: editSupplierCompanyId.value
      ? Number(editSupplierCompanyId.value)
      : null
  });

  const reasonValue = editReason.value || editReasonPreset.value || "수량 변경";

  await api.put(`/inventory/${editingCode.value}`, {
    quantity: Number(editQuantity.value || 0),
    reason: reasonValue
  });

  cancelEdit();
  await loadInventory();
  await loadProducts();
};

const changeProductCode = async () => {
  const nextCode = (editNewCode.value || "").trim();
  if (!editingCode.value) return;
  if (!nextCode) {
    alert("새 신품번을 입력하세요.");
    return;
  }
  if (nextCode === editingCode.value) {
    alert("현재 신품번과 같습니다.");
    return;
  }

  const ok = window.confirm(
    `신품번을 ${editingCode.value} 에서 ${nextCode}(으)로 변경할까요?\n관련 주문, BOM, 거래 이력 코드도 함께 변경됩니다.`
  );
  if (!ok) return;

  try {
    await api.put(`/products/${editingCode.value}/change-code`, {
      new_code: nextCode
    });
  } catch (err) {
    const message =
      err?.response?.data?.detail || "신품번 변경 중 오류가 발생했습니다.";
    alert(message);
    return;
  }

  if (selectedProduct.value === editingCode.value) {
    selectedProduct.value = nextCode;
  }
  editingCode.value = nextCode;
  editNewCode.value = nextCode;
  await loadInventory();
  await loadProducts();
  if (selectedProduct.value === nextCode) {
    await loadProductLogs(nextCode);
  }
  alert("신품번 변경 완료");
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
    const drawingValue = (item.drawing_number || "").toString().toLowerCase();
    const nameValue = (item.name || "").toString().toLowerCase();
    return (
      (keyword &&
        (
          codeValue.includes(keyword) ||
          oldValue.includes(keyword) ||
          drawingValue.includes(keyword)
        )) ||
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

const escapeHtml = (value) =>
  String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");

const saveInventoryPdf = () => {
  const timestamp = new Date().toLocaleString("ko-KR");
  const rows = inventoryReportRows.value.map((r, i) => `
    <tr>
      <td>${i + 1}</td>
      <td>${escapeHtml(r.code)}</td>
      <td>${escapeHtml(r.name || "-")}</td>
      <td class="num">${escapeHtml(r.quantity)}</td>
    </tr>
  `).join("");

  const html = `
    <!doctype html>
    <html lang="ko">
      <head>
        <meta charset="utf-8" />
        <title>재고 현황</title>
        <style>
          * { box-sizing: border-box; }
          body {
            margin: 24px;
            font-family: "Apple SD Gothic Neo", "Malgun Gothic", "Noto Sans KR", sans-serif;
            color: #0f172a;
          }
          h1 { font-size: 18px; margin: 0 0 6px; }
          .meta { font-size: 12px; margin-bottom: 12px; color: #475569; }
          table {
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
          }
          th, td {
            border: 1px solid #e2e8f0;
            padding: 6px 8px;
            text-align: left;
          }
          th { background: #f8fafc; font-weight: 600; }
          .num { text-align: right; }
        </style>
      </head>
      <body>
        <h1>재고 현황</h1>
        <div class="meta">생성일시: ${escapeHtml(timestamp)}</div>
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
            ${rows || "<tr><td colspan='4'>데이터 없음</td></tr>"}
          </tbody>
        </table>
      </body>
    </html>
  `;

  const win = window.open("", "_blank", "width=900,height=700");
  if (!win) {
    alert("팝업 차단을 해제해 주세요.");
    return;
  }
  win.document.write(html);
  win.document.close();
  win.focus();
  win.onload = () => {
    win.print();
    win.close();
  };
};

const exportInventoryExcel = () => {
  const rows = inventory.value
    .filter(
      (item) => (item.type || "PART").toString().toUpperCase() === "PART"
    )
    .map((item) => ({
      구품번: item.old_code || "",
      신품번: item.new_code || item.code || "",
      도번: item.drawing_number || "",
      품명: item.name || "",
      규격: item.spec || "",
      재질: item.material || "",
      열처리: item.heat_treatment || "",
      용접: item.welding || "",
      도금: item.plating || "",
      현재재고: Number(item.quantity || 0),
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

const handleGlobalClick = () => closeAllDropdowns();

onMounted(() => {
  loadInventory();
  loadProducts();
  loadCompanies();
  window.addEventListener("click", handleGlobalClick);
});

onUnmounted(() => {
  window.removeEventListener("click", handleGlobalClick);
  clearMapImageUrl();
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

const openPartsModal = (tab) => {
  partsModalTab.value = tab;
  showPartsManageModal.value = true;
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

const filteredStockInCodeSuggestions = computed(() => {
  const keyword = (stockInCode.value || "").trim().toLowerCase();
  if (!keyword) return [];
  return inventory.value
    .filter(
      (item) => (item.type || "PART").toString().toUpperCase() === "PART"
    )
    .filter((item) =>
      (item.new_code || item.code || "").toLowerCase().includes(keyword) ||
      (item.old_code || "").toLowerCase().includes(keyword)
    )
    .slice(0, 10);
});

const selectStockInCodeSuggestion = (codeValue) => {
  stockInCode.value = codeValue;
  showStockInCodeDropdown.value = false;
};

const filteredStockInNameSuggestions = computed(() => {
  const keyword = (stockInNameInput.value || "").trim().toLowerCase();
  if (!keyword) return [];
  return inventory.value
    .filter(
      (item) => (item.type || "PART").toString().toUpperCase() === "PART"
    )
    .filter((item) => (item.name || "").toLowerCase().includes(keyword))
    .slice(0, 10);
});

const selectStockInNameSuggestion = (nameValue) => {
  stockInNameInput.value = nameValue;
  showStockInNameDropdown.value = false;
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
      (item.old_code || "").toString().toLowerCase().includes(keyword) ||
      (item.drawing_number || "").toString().toLowerCase().includes(keyword)
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

  const buildUploadForm = (duplicateAction) => {
    const form = new FormData();
    form.append("file", uploadFile.value);
    form.append("duplicate_action", duplicateAction);
    return form;
  };

  let res;
  try {
    res = await api.post("/products/import-parts", buildUploadForm("prompt"), {
      headers: { "Content-Type": "multipart/form-data" }
    });
  } catch (err) {
    const detail = err?.response?.data?.detail;
    if (err?.response?.status === 409 && detail?.duplicate_count) {
      const previewCodes = Array.isArray(detail.duplicate_codes) && detail.duplicate_codes.length
        ? `\n중복 품번 예시: ${detail.duplicate_codes.join(", ")}`
        : "";
      const overwrite = window.confirm(
        `이미 등록된 단품 ${detail.duplicate_count}건이 있습니다.${previewCodes}\n\n확인: 기존 단품 덮어쓰기\n취소: 중복 단품 스킵`
      );
      const duplicateAction = overwrite ? "overwrite" : "skip";
      res = await api.post("/products/import-parts", buildUploadForm(duplicateAction), {
        headers: { "Content-Type": "multipart/form-data" }
      });
    } else {
      const message = detail?.message || detail || "엑셀 업로드 중 오류가 발생했습니다.";
      alert(message);
      return;
    }
  }

  uploadFile.value = null;
  if (uploadInputRef.value) {
    uploadInputRef.value.value = "";
  }
  await loadInventory();
  await loadProducts();
  // 업로드 중 발주처(Company)가 새로 생성될 수 있으니 목록을 갱신한다.
  await loadCompanies();
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

const refreshUpload = async () => {
  uploadFile.value = null;
  if (uploadInputRef.value) {
    uploadInputRef.value.value = "";
  }
  await loadInventory();
  await loadProducts();
  await loadCompanies();
};
</script>

<template>
  <div>

    <div class="flex items-center justify-between mb-6">
      <h2 class="page-title">📦 단품 관리</h2>
      <div class="flex gap-2 items-center">
        <button
          @click="openPartsModal('register')"
          class="btn btn-primary"
        >
          단품 등록
        </button>
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

    <!-- 단품 관리 모달 -->
    <div v-if="showPartsManageModal" class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-black/40" @click="showPartsManageModal = false"></div>
      <div class="relative bg-white w-[90vw] max-w-5xl max-h-[85vh] rounded-2xl shadow-xl overflow-hidden">
        <div class="flex items-center justify-between px-4 py-3 border-b">
        <div class="flex items-center gap-2">
          <button
            @click="partsModalTab = 'register'"
            :class="partsModalTab === 'register' ? 'btn btn-primary' : 'btn btn-secondary'"
          >
            단품 등록
          </button>
          <button
            @click="partsModalTab = 'upload'"
            :class="partsModalTab === 'upload' ? 'btn btn-success' : 'btn btn-secondary'"
          >
            엑셀 업로드
          </button>
          </div>
          <button class="btn btn-secondary" @click="showPartsManageModal = false">닫기</button>
        </div>
        <div class="p-4 overflow-auto max-h-[75vh]">
          <div v-if="partsModalTab === 'register'">
            <div class="panel">
              <div class="panel-header">단품 등록</div>
              <div class="p-3 flex flex-col gap-2">
                <div class="flex gap-2 items-center flex-wrap">
                  <input v-model="oldCodeInput"
                    placeholder="구품번"
                    class="input w-32" />

                  <input v-model="drawingNumberInput"
                    placeholder="도번"
                    class="input w-32" />

                  <div class="relative w-40" @click.stop>
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

                  <div class="relative w-56" @click.stop>
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

                  <div class="relative w-48" @click.stop>
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
          </div>

          <div v-else>
            <div class="panel">
              <div class="panel-header">엑셀 업로드</div>
              <div class="p-3 flex gap-2 items-center flex-wrap">
                <input ref="uploadInputRef" type="file" @change="onFileChange" class="input w-72" />
                <button @click="uploadPartsExcel" class="btn btn-success">업로드</button>
                <button @click="refreshUpload" class="btn btn-secondary">새로고침</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 입고 -->
    <div class="panel mb-4">
      <div class="panel-header">입고</div>
      <div class="p-3 flex gap-2 items-center flex-wrap">
        <div class="relative w-48" @click.stop>
          <input
            v-model="stockInCode"
            @focus="showStockInCodeDropdown = true"
            @blur="deferHide(() => showStockInCodeDropdown = false)"
            placeholder="구/신품번"
            class="input w-full"
          />
          <div
            v-if="showStockInCodeDropdown && filteredStockInCodeSuggestions.length"
            class="absolute bg-white border w-full z-10 max-h-40 overflow-y-auto rounded-lg shadow"
          >
            <div
              v-for="item in filteredStockInCodeSuggestions"
              :key="`stock-code-${item.new_code || item.code}`"
              @click="selectStockInCodeSuggestion(item.new_code || item.code)"
              class="p-2 hover:bg-slate-100 cursor-pointer text-sm"
            >
              {{ item.new_code || item.code }} / {{ item.old_code || "-" }} ({{ item.name }})
            </div>
          </div>
        </div>

        <div class="relative w-56" @click.stop>
          <input
            v-model="stockInNameInput"
            @focus="showStockInNameDropdown = true"
            @blur="deferHide(() => showStockInNameDropdown = false)"
            placeholder="품명"
            class="input w-full"
          />
          <div
            v-if="showStockInNameDropdown && filteredStockInNameSuggestions.length"
            class="absolute bg-white border w-full z-10 max-h-40 overflow-y-auto rounded-lg shadow"
          >
            <div
              v-for="item in filteredStockInNameSuggestions"
              :key="`stock-name-${item.new_code || item.code}`"
              @click="selectStockInNameSuggestion(item.name)"
              class="p-2 hover:bg-slate-100 cursor-pointer text-sm"
            >
              {{ item.name }} ({{ item.new_code || item.code }})
            </div>
          </div>
        </div>

        <input
          v-model="stockInQuantity"
          type="number"
          placeholder="입고수량"
          class="input w-24"
        />

        <input
          v-model="stockInReason"
          placeholder="사유 (선택)"
          class="input w-48"
        />

        <button @click="stockIn" class="btn btn-primary">
          입고
        </button>
      </div>
    </div>

    <!-- 검색 -->
    <div class="panel mb-6">
      <div class="panel-header">부품 검색</div>
      <div class="p-3 flex gap-2 items-center flex-wrap">

      <div class="relative w-48" @click.stop>
        <input v-model="searchCode"
          placeholder="구/신품번/도번 검색"
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
            {{ item.new_code || item.code }} / {{ item.old_code || "-" }} / {{ item.drawing_number || "-" }} ({{ item.name }})
          </div>
        </div>
      </div>

      <div class="relative w-56" @click.stop>
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
        전체정보 보기
      </button>

      </div>
    </div>

    <!-- 전체 단품 모달 -->
    <div v-if="showAllPartsModal" class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-black/40" @click="showAllPartsModal = false"></div>
      <div class="relative bg-white w-[95vw] max-w-7xl max-h-[85vh] rounded-2xl shadow-xl overflow-hidden">
        <div class="flex items-center justify-between px-4 py-3 border-b">
          <div class="font-semibold">전체 단품 정보 ({{ allPartsSorted.length }})</div>
          <button class="btn btn-secondary" @click="showAllPartsModal = false">닫기</button>
        </div>
        <div class="p-3 overflow-auto max-h-[75vh]">
          <table class="w-full text-left table-nowrap">
            <thead class="table-head">
              <tr>
                <th class="p-2">구품번</th>
                <th class="p-2">신품번</th>
                <th class="p-2 min-w-[220px]">도번</th>
                <th class="p-2">품명</th>
                <th class="p-2">재질</th>
                <th class="p-2">규격</th>
                <th class="px-2 py-2 text-xs text-center min-w-[56px]">열처리</th>
                <th class="px-2 py-2 text-xs text-center min-w-[56px]">용접</th>
                <th class="px-2 py-2 text-xs text-center min-w-[56px]">도금</th>
                <th class="p-2">현재재고</th>
                <th class="p-2">최소재고</th>
                <th class="p-2">보관위치</th>
                <th class="p-2">발주처</th>
                <th class="p-2">관리</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in allPartsSorted" :key="`modal-${item.new_code || item.code}`" class="border-t hover:bg-slate-50">
                <td class="p-2 font-medium">{{ item.old_code || "-" }}</td>
                <td class="p-2">{{ item.new_code || "-" }}</td>
                <td class="p-2">
                  <div class="max-w-[320px] truncate" :title="item.drawing_number || '-'">
                    {{ item.drawing_number || "-" }}
                  </div>
                </td>
                <td class="p-2">{{ item.name || "-" }}</td>
                <td class="p-2">{{ item.material || "-" }}</td>
                <td class="p-2">{{ item.spec || "-" }}</td>
                <td class="px-2 py-2 text-center">{{ item.heat_treatment || "-" }}</td>
                <td class="px-2 py-2 text-center">{{ item.welding || "-" }}</td>
                <td class="px-2 py-2 text-center">{{ item.plating || "-" }}</td>
                <td class="p-2">{{ item.quantity }}</td>
                <td class="p-2">{{ item.min_stock }}</td>
                <td class="p-2">
                  <button
                    v-if="item.location"
                    class="text-slate-900 underline underline-offset-2 hover:text-sky-700"
                    @click.stop="openLocationMap(item.location, item)"
                    :title="`배치도에서 ${item.location} 위치 바로 보기`"
                  >
                    {{ item.location }}
                  </button>
                  <span v-else>-</span>
                </td>
                <td class="p-2">{{ getCompanyName(item.supplier_company_id) }}</td>
                <td class="p-2">
                  <div class="flex gap-2">
                    <button
                      @click="startEdit(item); showAllPartsModal = false"
                      class="btn btn-info h-7 px-2 text-xs"
                    >
                      수정
                    </button>
                    <button
                      @click="deleteInventoryItem(item.new_code || item.code)"
                      class="btn btn-danger h-7 px-2 text-xs"
                    >
                      삭제
                    </button>
                  </div>
                </td>
              </tr>
              <tr v-if="allPartsSorted.length === 0">
                <td colspan="14" class="p-4 text-center text-gray-400">목록이 없습니다.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- 배치도 위치 모달 -->
    <div v-if="showLocationMapModal" class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-black/40" @click="closeLocationMap"></div>
      <div class="relative bg-white w-[95vw] max-w-6xl max-h-[90vh] rounded-2xl shadow-xl overflow-hidden">
        <div class="flex items-center justify-between px-4 py-3 border-b">
          <div class="font-semibold">
            공장 배치도 ({{ mapLocationCode || "-" }})
          </div>
          <div class="flex items-center gap-2">
            <button
              v-if="false"
              class="btn btn-secondary h-8 px-2 text-xs"
              @click="toggleMapEditMode"
              :class="mapEditMode ? 'bg-slate-900 text-white border-slate-900 hover:bg-slate-800' : ''"
              :title="mapEditMode ? '좌표 편집 모드 종료' : '좌표 편집 모드 (지도 클릭으로 좌표 등록/이동)'"
            >
              {{ mapEditMode ? "편집중" : "좌표편집" }}
            </button>
            <button
              v-if="mapEditMode"
              class="btn btn-primary h-8 px-2 text-xs"
              @click="savePendingPoint"
              :disabled="!mapPendingPoint"
              :class="!mapPendingPoint ? 'opacity-50 cursor-not-allowed' : ''"
              title="클릭한 좌표를 저장"
            >
              좌표저장
            </button>
            <button class="btn btn-primary h-8 px-3 text-xs" @click="downloadLocationMapExcel">
              엑셀 다운로드
            </button>
            <button class="btn btn-secondary h-8 px-2 text-xs" @click="zoomOutMap">-</button>
            <input
              v-model.number="mapZoom"
              type="range"
              min="0.6"
              max="2.6"
              step="0.05"
              class="w-40"
              aria-label="배치도 확대/축소"
            />
            <button class="btn btn-secondary h-8 px-2 text-xs" @click="zoomInMap">+</button>
            <button class="btn btn-secondary h-8 px-2 text-xs" @click="resetMapZoom">원본</button>
            <button class="btn btn-secondary" @click="closeLocationMap">닫기</button>
          </div>
        </div>
        <div class="p-4 overflow-auto max-h-[82vh]">
          <div class="relative inline-block origin-top-left" :style="{ transform: `scale(${mapZoom})` }">
            <img
              :src="mapImageUrl || factoryLayoutUrl"
              alt="공장 배치도"
              class="w-full h-auto block select-none rounded-xl border border-slate-200"
              :class="mapImageLoading ? 'opacity-50' : ''"
              draggable="false"
              @click.stop="onMapClick"
            />

            <template v-if="false && adjustedLocationBox">
              <div
                class="absolute -translate-x-1/2 -translate-y-1/2 pointer-events-none"
                :style="{
                  left: `${adjustedLocationBox.cx}%`,
                  top: `${adjustedLocationBox.cy}%`,
                  width: `${adjustedLocationBox.w}%`,
                  height: `${adjustedLocationBox.h}%`
                }"
                aria-hidden="true"
              >
                <div
                  class="w-full h-full"
                  :class="mapHighlightClass"
                ></div>
              </div>
            </template>

            <template v-else-if="false && displayLocationPoint">
              <div
                class="absolute -translate-x-1/2 -translate-y-1/2 pointer-events-none"
                :style="{ left: `${displayLocationPoint.x}%`, top: `${displayLocationPoint.y}%` }"
                aria-hidden="true"
              >
                <div class="relative">
                  <!-- Arrow pointer -->
                  <div
                    class="absolute left-1/2 -translate-x-1/2 -top-5 w-0 h-0"
                    style="border-left: 10px solid transparent; border-right: 10px solid transparent; border-bottom: 14px solid #0f172a;"
                  ></div>
                  <div
                    class="absolute left-1/2 -translate-x-1/2 -top-6 w-0 h-0"
                    style="border-left: 12px solid transparent; border-right: 12px solid transparent; border-bottom: 16px solid white;"
                  ></div>

                  <!-- Pulse ring -->
                  <div class="absolute inset-0 rounded-full bg-black/25 blur-[1px]"></div>
                  <div class="absolute inset-0 rounded-full bg-slate-900/15 animate-ping"></div>

                  <!-- Dot -->
                  <div class="w-6 h-6 rounded-full bg-black border-2 border-white shadow-lg"></div>

                  <!-- Label -->
                  <div class="absolute left-1/2 -translate-x-1/2 top-7 text-xs font-semibold px-2 py-0.5 rounded-full bg-white/95 border border-slate-200 shadow">
                    {{ mapLocationCode }}
                  </div>
                </div>
              </div>
            </template>
            <div
              v-if="mapImageLoading || mapImageError"
              class="absolute left-3 top-3 bg-white/90 border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 shadow"
            >
              {{ mapImageLoading ? "배치도 이미지를 만드는 중입니다..." : mapImageError }}
            </div>
          </div>
          <div class="mt-3 text-xs text-slate-500">
            이미지는 엑셀 셀 기준으로 생성됩니다. 필요하면 상단의 엑셀 다운로드 버튼으로 파일도 받을 수 있습니다.
          </div>
          <div v-if="false && mapEditMode" class="mt-2 text-xs text-slate-600">
            편집 모드: 배치도에서 위치를 클릭하면 마커가 이동합니다. 저장하려면 `좌표저장`을 누르세요.
          </div>
        </div>
      </div>
    </div>

    <!-- 수정 -->
    <div v-if="editingCode" class="panel p-3 mb-6">
      <div class="font-semibold mb-2">재고 정보 수정: {{ editingCode }}</div>
      <div class="mb-3 flex flex-wrap gap-3 items-end rounded-xl bg-slate-50 p-3">
        <label class="flex flex-col gap-1 text-sm text-slate-600">
          <span>현재 신품번</span>
          <input :value="editingCode" class="input w-40 bg-slate-100" readonly />
        </label>
        <label class="flex flex-col gap-1 text-sm text-slate-600">
          <span>새 신품번</span>
          <input v-model="editNewCode" class="input w-40" />
        </label>
        <button @click="changeProductCode" class="btn btn-info">
          신품번 변경
        </button>
      </div>
      <div class="flex flex-wrap gap-3 items-end">
        <label class="flex flex-col gap-1 text-sm text-slate-600">
          <span>구품번</span>
          <input v-model="editOldCode" class="input w-32" />
        </label>
        <label class="flex flex-col gap-1 text-sm text-slate-600">
          <span>도번</span>
          <input v-model="editDrawingNumber" class="input w-32" />
        </label>
        <label class="flex flex-col gap-1 text-sm text-slate-600">
          <span>제품명</span>
          <input v-model="editName" class="input w-40" />
        </label>
        <label class="flex flex-col gap-1 text-sm text-slate-600">
          <span>재질</span>
          <input v-model="editMaterial" class="input w-28" />
        </label>
        <label class="flex flex-col gap-1 text-sm text-slate-600">
          <span>규격</span>
          <input v-model="editSpec" class="input w-28" />
        </label>
        <label class="flex flex-col gap-1 text-sm text-slate-600">
          <span>열처리</span>
          <input v-model="editHeatTreatment" class="input w-24" />
        </label>
        <label class="flex flex-col gap-1 text-sm text-slate-600">
          <span>용접</span>
          <input v-model="editWelding" class="input w-24" />
        </label>
        <label class="flex flex-col gap-1 text-sm text-slate-600">
          <span>도금</span>
          <input v-model="editPlating" class="input w-24" />
        </label>
        <label class="flex flex-col gap-1 text-sm text-slate-600">
          <span>보관위치</span>
          <input v-model="editLocation" class="input w-32" />
        </label>
        <button
          class="btn btn-secondary h-9 px-3"
          @click="openLocationMap(editLocation, { quantity: editQuantity, min_stock: editMinStock })"
          :disabled="!editLocation"
          :class="!editLocation ? 'opacity-50 cursor-not-allowed' : ''"
          title="배치도에서 보관위치 바로 보기"
        >
          배치도 보기
        </button>
        <label class="flex flex-col gap-1 text-sm text-slate-600">
          <span>발주처</span>
          <select v-model="editSupplierCompanyId" class="input w-40">
            <option value="">발주처 선택</option>
            <option v-for="c in companies" :key="c.id" :value="String(c.id)">
              {{ c.name }}
            </option>
          </select>
        </label>
        <label class="flex flex-col gap-1 text-sm text-slate-600">
          <span>최소재고</span>
          <input v-model="editMinStock" type="number" class="input w-24" />
        </label>
        <label class="flex flex-col gap-1 text-sm text-slate-600">
          <span>현재재고</span>
          <input v-model="editQuantity" type="number" class="input w-24" />
        </label>
        <label class="flex flex-col gap-1 text-sm text-slate-600">
          <span>사유 선택</span>
          <select v-model="editReasonPreset" class="input w-28">
            <option value="">사유 선택</option>
            <option value="결손">결손</option>
            <option value="불량">불량</option>
            <option value="재고 정리">재고 정리</option>
          </select>
        </label>
        <label class="flex flex-col gap-1 text-sm text-slate-600">
          <span>수량 변경 사유</span>
          <input v-model="editReason" placeholder="직접 입력"
            class="input w-48" />
        </label>

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
    <div class="panel overflow-x-auto">
      <table class="w-full text-left table-nowrap">

        <thead class="table-head">
          <tr>
            <th class="p-3">구품번</th>
            <th class="p-3">신품번</th>
            <th class="p-3 min-w-[260px]">도번</th>
            <th class="p-3">품명</th>
            <th class="p-3">재질</th>
            <th class="p-3">규격</th>
            <th class="px-2 py-3 text-xs text-center min-w-[64px]">열처리</th>
            <th class="px-2 py-3 text-xs text-center min-w-[64px]">용접</th>
            <th class="px-2 py-3 text-xs text-center min-w-[64px]">도금</th>
            <th class="p-3">현재재고</th>
            <th class="p-3">최소재고</th>
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

            <td class="p-3">
              <div class="max-w-[360px] truncate" :title="item.drawing_number || '-'">
                {{ item.drawing_number || "-" }}
              </div>
            </td>

            <td class="p-3">{{ item.name || "-" }}</td>

            <td class="p-3">{{ item.material || "-" }}</td>

            <td class="p-3">{{ item.spec || "-" }}</td>

            <td class="px-2 py-3 text-center">{{ item.heat_treatment || "-" }}</td>

            <td class="px-2 py-3 text-center">{{ item.welding || "-" }}</td>

            <td class="px-2 py-3 text-center">{{ item.plating || "-" }}</td>

            <td
              class="p-3 font-bold"
              :class="item.quantity < item.min_stock ? 'text-red-500' : 'text-blue-600'"
            >
              {{ item.quantity }}
            </td>

            <td class="p-3">{{ item.min_stock }}</td>

            <td class="p-3">
              <button
                v-if="item.location"
                class="text-slate-900 underline underline-offset-2 hover:text-sky-700"
                @click.stop="openLocationMap(item.location, item)"
                :title="`배치도에서 ${item.location} 위치 바로 보기`"
              >
                {{ item.location }}
              </button>
              <span v-else>-</span>
            </td>

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

      <div class="panel overflow-x-auto">
        <table class="w-full text-left table-nowrap">

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
