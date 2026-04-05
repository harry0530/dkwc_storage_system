<script setup>
import { ref, onMounted, computed } from "vue";
import api from "../api";

const companies = ref([]);

const name = ref("");
const phone = ref("");
const fax = ref("");        // ⭐ 추가
const address = ref("");
const companySearch = ref("");

// 수정
const editingCompanyId = ref("");
const editName = ref("");
const editPhone = ref("");
const editFax = ref("");
const editAddress = ref("");

const loadCompanies = async () => {
  const res = await api.get("/companies/");
  companies.value = res.data;
};

const createCompany = async () => {
  if (!name.value) return;

  await api.post("/companies/", {
    name: name.value,
    phone: phone.value,
    fax: fax.value,
    address: address.value
  });

  name.value = "";
  phone.value = "";
  fax.value = "";
  address.value = "";

  loadCompanies();
};

const filteredCompanies = computed(() => {
  const keyword = (companySearch.value || "").trim().toLowerCase();
  if (!keyword) return companies.value;
  return companies.value.filter((c) =>
    (c.name || "").toLowerCase().includes(keyword) ||
    (c.phone || "").toLowerCase().includes(keyword) ||
    (c.fax || "").toLowerCase().includes(keyword) ||
    (c.address || "").toLowerCase().includes(keyword)
  );
});

const startEditCompany = (c) => {
  editingCompanyId.value = String(c.id);
  editName.value = c.name || "";
  editPhone.value = c.phone || "";
  editFax.value = c.fax || "";
  editAddress.value = c.address || "";
};

const cancelEditCompany = () => {
  editingCompanyId.value = "";
  editName.value = "";
  editPhone.value = "";
  editFax.value = "";
  editAddress.value = "";
};

const saveEditCompany = async (id) => {
  await api.put(`/companies/${id}`, {
    name: editName.value,
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

onMounted(loadCompanies);
</script>

<template>
  <div>

    <h2 class="page-title mb-6">🏢 거래처 관리</h2>

    <div class="panel p-3 mb-6 flex gap-2 flex-wrap">

      <input v-model="name" placeholder="회사명"
        class="input w-40" />

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

    <div class="panel overflow-hidden">
      <div class="p-3 border-b bg-slate-50">
        <input
          v-model="companySearch"
          placeholder="회사명/전화번호/팩스/주소 검색"
          class="input w-72"
        />
      </div>

      <table class="w-full text-left">

        <thead class="table-head">
          <tr>
            <th class="p-3">회사명</th>
            <th class="p-3">전화번호</th>
            <th class="p-3">팩스</th>
            <th class="p-3">주소</th>
            <th class="p-3">관리</th>
          </tr>
        </thead>

        <tbody>
          <tr v-for="c in filteredCompanies" :key="c.id"
            class="border-t hover:bg-gray-50">

            <template v-if="editingCompanyId === String(c.id)">
              <td class="p-3">
                <input v-model="editName" class="input w-32 h-8" />
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
              <td class="p-3 font-semibold">{{ c.name }}</td>
              <td class="p-3">{{ c.phone }}</td>
              <td class="p-3">{{ c.fax }}</td>
              <td class="p-3">{{ c.address }}</td>
              <td class="p-3">
                <div class="flex gap-2">
                  <button @click="startEditCompany(c)"
                    class="btn btn-info h-8 px-2 text-xs">
                    수정
                  </button>
                  <button @click="deleteCompany(c.id)"
                    class="btn btn-danger h-8 px-2 text-xs">
                    삭제
                  </button>
                </div>
              </td>
            </template>

          </tr>
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
