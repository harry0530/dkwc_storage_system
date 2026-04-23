<script setup>
import { ref, onMounted, computed } from "vue";
import api from "../api";

const companies = ref([]);
const employeesByCompany = ref({});
const allEmployees = ref([]);
const expandedCompanyId = ref("");

const name = ref("");
const email = ref("");
const phone = ref("");
const fax = ref("");        // ⭐ 추가
const address = ref("");
const companySearch = ref("");
const sortKey = ref("name");
const sortDir = ref("asc");

// 수정
const editingCompanyId = ref("");
const editName = ref("");
const editEmail = ref("");
const editPhone = ref("");
const editFax = ref("");
const editAddress = ref("");

// 직원 입력
const employeeDraftByCompany = ref({});

// 직원 수정
const editingEmployeeId = ref("");
const editEmpDepartment = ref("");
const editEmpName = ref("");
const editEmpTitle = ref("");
const editEmpPhone = ref("");
const editEmpEmail = ref("");

const loadCompanies = async () => {
  const res = await api.get("/companies/");
  companies.value = res.data;

  // Ensure per-company employee drafts exist so v-model bindings are stable.
  const next = { ...(employeeDraftByCompany.value || {}) };
  for (const c of companies.value || []) {
    const key = String(c?.id ?? "");
    if (!key) continue;
    if (!next[key]) {
      next[key] = { department: "", name: "", title: "", phone: "", email: "" };
    }
  }
  employeeDraftByCompany.value = next;
};

const loadAllEmployees = async () => {
  const res = await api.get("/companies/employees");
  allEmployees.value = Array.isArray(res.data) ? res.data : [];
};

const loadEmployees = async (companyId) => {
  const res = await api.get(`/companies/${companyId}/employees`);
  employeesByCompany.value = {
    ...employeesByCompany.value,
    [companyId]: res.data
  };
};

const createCompany = async () => {
  if (!name.value) return;

  await api.post("/companies/", {
    name: name.value,
    email: email.value,
    phone: phone.value,
    fax: fax.value,
    address: address.value
  });

  name.value = "";
  email.value = "";
  phone.value = "";
  fax.value = "";
  address.value = "";

  loadCompanies();
};

const filteredCompanies = computed(() => {
  const keyword = (companySearch.value || "").trim().toLowerCase();
  if (!keyword) return companies.value;

  const byCompanyId = new Map();
  for (const e of allEmployees.value || []) {
    const cid = String(e.company_id || "");
    if (!cid) continue;
    if (!byCompanyId.has(cid)) byCompanyId.set(cid, []);
    byCompanyId.get(cid).push(e);
  }

  return companies.value.filter((c) =>
    (c.name || "").toLowerCase().includes(keyword) ||
    (c.email || "").toLowerCase().includes(keyword) ||
    (c.phone || "").toLowerCase().includes(keyword) ||
    (c.fax || "").toLowerCase().includes(keyword) ||
    (c.address || "").toLowerCase().includes(keyword) ||
    (byCompanyId.get(String(c.id)) || []).some((e) => {
      const en = (e?.name || "").toLowerCase();
      const ee = (e?.email || "").toLowerCase();
      return en.includes(keyword) || ee.includes(keyword);
    })
  );
});

const compareText = (a, b) => {
  const aa = (a || "").toString();
  const bb = (b || "").toString();
  return aa.localeCompare(bb, "ko", { sensitivity: "base" });
};

const getSortValue = (c, key) => {
  if (!c) return "";
  if (key === "name") return c.name;
  if (key === "email") return c.email;
  if (key === "phone") return c.phone;
  if (key === "fax") return c.fax;
  if (key === "address") return c.address;
  return "";
};

const sortedCompanies = computed(() => {
  const base = [...filteredCompanies.value];
  const dir = sortDir.value === "asc" ? 1 : -1;
  const key = sortKey.value;
  return base.sort((a, b) => {
    return compareText(getSortValue(a, key), getSortValue(b, key)) * dir;
  });
});

const toggleSort = (key) => {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === "asc" ? "desc" : "asc";
  } else {
    sortKey.value = key;
    sortDir.value = "asc";
  }
};

const sortIndicator = (key) => {
  if (sortKey.value !== key) return "";
  return sortDir.value === "asc" ? "▲" : "▼";
};

const startEditCompany = (c) => {
  editingCompanyId.value = String(c.id);
  editName.value = c.name || "";
  editEmail.value = c.email || "";
  editPhone.value = c.phone || "";
  editFax.value = c.fax || "";
  editAddress.value = c.address || "";
};

const cancelEditCompany = () => {
  editingCompanyId.value = "";
  editName.value = "";
  editEmail.value = "";
  editPhone.value = "";
  editFax.value = "";
  editAddress.value = "";
};

const saveEditCompany = async (id) => {
  await api.put(`/companies/${id}`, {
    name: editName.value,
    email: editEmail.value,
    phone: editPhone.value,
    fax: editFax.value,
    address: editAddress.value
  });
  cancelEditCompany();
  loadCompanies();
};

const deleteCompany = async (id) => {
  const ok = window.confirm("거래처를 삭제할까요?");
  if (!ok) return;
  await api.delete(`/companies/${id}`);
  loadCompanies();
};

const toggleEmployees = async (companyId) => {
  const target = String(companyId);
  if (expandedCompanyId.value === target) {
    expandedCompanyId.value = "";
    return;
  }
  expandedCompanyId.value = target;
  if (!employeesByCompany.value[target]) {
    await loadEmployees(target);
  }
};

const addEmployee = async (companyId) => {
  const key = String(companyId);
  const draft = employeeDraftByCompany.value?.[key] || {
    department: "",
    name: "",
    title: "",
    phone: "",
    email: ""
  };

  if (!String(draft.name || "").trim()) return;
  await api.post(`/companies/${companyId}/employees`, {
    department: draft.department,
    name: draft.name,
    title: draft.title,
    phone: draft.phone,
    email: draft.email
  });

  employeeDraftByCompany.value = {
    ...(employeeDraftByCompany.value || {}),
    [key]: { department: "", name: "", title: "", phone: "", email: "" }
  };

  await loadEmployees(String(companyId));
  await loadAllEmployees();
};

const deleteEmployee = async (employeeId, companyId) => {
  await api.delete(`/companies/employees/${employeeId}`);
  await loadEmployees(String(companyId));
  await loadAllEmployees();
};

const startEditEmployee = (emp) => {
  editingEmployeeId.value = String(emp.id);
  editEmpDepartment.value = emp.department || "";
  editEmpName.value = emp.name || "";
  editEmpTitle.value = emp.title || "";
  editEmpPhone.value = emp.phone || "";
  editEmpEmail.value = emp.email || "";
};

const cancelEditEmployee = () => {
  editingEmployeeId.value = "";
  editEmpDepartment.value = "";
  editEmpName.value = "";
  editEmpTitle.value = "";
  editEmpPhone.value = "";
  editEmpEmail.value = "";
};

const saveEditEmployee = async (employeeId, companyId) => {
  await api.put(`/companies/employees/${employeeId}`, {
    department: editEmpDepartment.value,
    name: editEmpName.value,
    title: editEmpTitle.value,
    phone: editEmpPhone.value,
    email: editEmpEmail.value
  });
  cancelEditEmployee();
  await loadEmployees(String(companyId));
  await loadAllEmployees();
};

onMounted(async () => {
  await loadCompanies();
  await loadAllEmployees();
});
</script>

<template>
  <div>

    <h2 class="page-title mb-6">🏢 거래처 관리</h2>

    <div class="panel p-3 mb-6 flex gap-2 flex-wrap">

      <input v-model="name" placeholder="회사명"
        class="input w-40" />

      <input v-model="email" placeholder="이메일"
        class="input w-48" />

      <input v-model="phone" placeholder="전화번호"
        class="input w-40" />

      <input v-model="fax" placeholder="팩스"
        class="input w-40" />

      <input v-model="address" placeholder="주소"
        class="input w-60" />

      <button @click="createCompany"
        class="btn btn-primary">
        등록
      </button>

    </div>

    <div class="panel overflow-x-auto">
      <div class="p-3 border-b bg-slate-50">
        <input
          v-model="companySearch"
          placeholder="회사명/이메일/전화번호/팩스/주소/직원이름 검색"
          class="input w-72"
        />
      </div>

      <table class="w-full text-left table-nowrap">

        <thead class="table-head">
          <tr>
            <th class="p-3 cursor-pointer select-none" @click="toggleSort('name')">회사명 {{ sortIndicator('name') }}</th>
            <th class="p-3 cursor-pointer select-none" @click="toggleSort('email')">이메일 {{ sortIndicator('email') }}</th>
            <th class="p-3 cursor-pointer select-none" @click="toggleSort('phone')">전화번호 {{ sortIndicator('phone') }}</th>
            <th class="p-3 cursor-pointer select-none" @click="toggleSort('fax')">팩스 {{ sortIndicator('fax') }}</th>
            <th class="p-3 cursor-pointer select-none" @click="toggleSort('address')">주소 {{ sortIndicator('address') }}</th>
            <th class="p-3">관리</th>
          </tr>
        </thead>

        <tbody>
          <template v-for="c in sortedCompanies" :key="c.id">
            <tr class="border-t hover:bg-gray-50">

            <template v-if="editingCompanyId === String(c.id)">
              <td class="p-3">
                <input v-model="editName" class="input w-32 h-8" />
              </td>
              <td class="p-3">
                <input v-model="editEmail" class="input w-40 h-8" />
              </td>
              <td class="p-3">
                <input v-model="editPhone" class="input w-32 h-8" />
              </td>
              <td class="p-3">
                <input v-model="editFax" class="input w-32 h-8" />
              </td>
              <td class="p-3">
                <input v-model="editAddress" class="input w-48 h-8" />
              </td>
              <td class="p-3">
                <div class="flex gap-2">
                  <button @click="saveEditCompany(c.id)"
                    class="btn btn-info h-8 px-2 text-xs">
                    저장
                  </button>
                  <button @click="cancelEditCompany"
                    class="btn btn-secondary h-8 px-2 text-xs">
                    취소
                  </button>
                </div>
              </td>
            </template>
            <template v-else>
              <td class="p-3 font-semibold cursor-pointer"
                @click="toggleEmployees(c.id)">
                {{ c.name }}
              </td>
              <td class="p-3">{{ c.email }}</td>
              <td class="p-3">{{ c.phone }}</td>
              <td class="p-3">{{ c.fax }}</td>
              <td class="p-3">{{ c.address }}</td>
              <td class="p-3">
                <div class="flex flex-wrap gap-2 items-center" @click.stop>
                  <button @click="startEditCompany(c)"
                    class="btn btn-info h-8 px-2 text-xs">
                    수정
                  </button>
                  <button @click="deleteCompany(c.id)"
                    class="btn btn-danger h-8 px-2 text-xs">
                    삭제
                  </button>

                  <div class="h-6 w-px bg-slate-200 mx-1"></div>

                  <input
                    v-model="employeeDraftByCompany[String(c.id)].name"
                    placeholder="직원이름"
                    class="input h-8 w-28"
                  />
                  <input
                    v-model="employeeDraftByCompany[String(c.id)].department"
                    placeholder="부서"
                    class="input h-8 w-24"
                  />
                  <input
                    v-model="employeeDraftByCompany[String(c.id)].title"
                    placeholder="직급"
                    class="input h-8 w-24"
                  />
                  <input
                    v-model="employeeDraftByCompany[String(c.id)].phone"
                    placeholder="전화"
                    class="input h-8 w-32"
                  />
                  <input
                    v-model="employeeDraftByCompany[String(c.id)].email"
                    placeholder="이메일"
                    class="input h-8 w-44"
                  />
                  <button
                    @click="addEmployee(c.id)"
                    class="btn btn-primary h-8 px-2 text-xs"
                    title="직원 추가"
                  >
                    직원추가
                  </button>
                </div>
              </td>
            </template>

            </tr>
            <tr v-if="expandedCompanyId === String(c.id)" class="border-t bg-slate-50/70">
              <td colspan="6" class="p-3">
                <div class="text-xs text-slate-500 mb-3">
                  직원 추가는 위 "관리" 칸에서 입력 후 직원추가 버튼을 눌러주세요.
                </div>

                <div class="overflow-x-auto">
                  <table class="w-full text-left text-sm table-nowrap">
                    <thead class="table-head">
                      <tr>
                        <th class="p-2">부서</th>
                        <th class="p-2">이름</th>
                        <th class="p-2">직급</th>
                        <th class="p-2">전화번호</th>
                        <th class="p-2">이메일</th>
                        <th class="p-2">관리</th>
                      </tr>
                    </thead>
                    <tbody>
                      <template v-for="emp in employeesByCompany[String(c.id)] || []" :key="emp.id">
                        <tr class="border-t">
                          <template v-if="editingEmployeeId === String(emp.id)">
                            <td class="p-2">
                              <input v-model="editEmpDepartment" class="input h-8 w-28" />
                            </td>
                            <td class="p-2">
                              <input v-model="editEmpName" class="input h-8 w-28" />
                            </td>
                            <td class="p-2">
                              <input v-model="editEmpTitle" class="input h-8 w-28" />
                            </td>
                            <td class="p-2">
                              <input v-model="editEmpPhone" class="input h-8 w-36" />
                            </td>
                            <td class="p-2">
                              <input v-model="editEmpEmail" class="input h-8 w-44" />
                            </td>
                            <td class="p-2">
                              <div class="flex gap-2">
                                <button
                                  @click="saveEditEmployee(emp.id, c.id)"
                                  class="btn btn-info h-7 px-2 text-xs"
                                >
                                  저장
                                </button>
                                <button
                                  @click="cancelEditEmployee"
                                  class="btn btn-secondary h-7 px-2 text-xs"
                                >
                                  취소
                                </button>
                              </div>
                            </td>
                          </template>
                          <template v-else>
                            <td class="p-2">{{ emp.department || "-" }}</td>
                            <td class="p-2">{{ emp.name || "-" }}</td>
                            <td class="p-2">{{ emp.title || "-" }}</td>
                            <td class="p-2">{{ emp.phone || "-" }}</td>
                            <td class="p-2">{{ emp.email || "-" }}</td>
                            <td class="p-2">
                              <div class="flex gap-2">
                                <button
                                  @click="startEditEmployee(emp)"
                                  class="btn btn-secondary h-7 px-2 text-xs"
                                >
                                  수정
                                </button>
                                <button
                                  @click="deleteEmployee(emp.id, c.id)"
                                  class="btn btn-danger h-7 px-2 text-xs"
                                >
                                  삭제
                                </button>
                              </div>
                            </td>
                          </template>
                        </tr>
                      </template>
                      <tr v-if="(employeesByCompany[String(c.id)] || []).length === 0">
                        <td colspan="6" class="p-3 text-center text-gray-400">
                          직원 정보가 없습니다.
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </td>
            </tr>
          </template>
        </tbody>

      </table>

      <div
        v-if="filteredCompanies.length === 0"
        class="p-4 text-sm text-gray-500"
      >
        검색 결과가 없습니다.
      </div>
    </div>

  </div>
</template>
