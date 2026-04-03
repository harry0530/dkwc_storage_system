<script setup>
import { ref, onMounted, computed } from "vue";
import api from "../api";

const companies = ref([]);

const name = ref("");
const phone = ref("");
const fax = ref("");        // ⭐ 추가
const address = ref("");
const companySearch = ref("");

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

onMounted(loadCompanies);
</script>

<template>
  <div>

    <h2 class="text-3xl font-bold mb-6">🏢 거래처 관리</h2>

    <div class="bg-white shadow rounded-xl p-3 mb-6 flex gap-2 flex-wrap">

      <input v-model="name" placeholder="회사명"
        class="border px-3 py-1 h-9 rounded w-40" />

      <input v-model="phone" placeholder="전화번호"
        class="border px-3 py-1 h-9 rounded w-40" />

      <input v-model="fax" placeholder="팩스"
        class="border px-3 py-1 h-9 rounded w-40" />

      <input v-model="address" placeholder="주소"
        class="border px-3 py-1 h-9 rounded w-60" />

      <button @click="createCompany"
        class="bg-blue-500 text-white px-4 h-9 rounded">
        등록
      </button>

    </div>

    <div class="bg-white shadow rounded-xl overflow-hidden">
      <div class="p-3 border-b bg-gray-50">
        <input
          v-model="companySearch"
          placeholder="회사명/전화번호/팩스/주소 검색"
          class="border px-2 py-1 h-9 rounded w-72 text-sm"
        />
      </div>

      <table class="w-full text-left">

        <thead class="bg-gray-100">
          <tr>
            <th class="p-3">회사명</th>
            <th class="p-3">전화번호</th>
            <th class="p-3">팩스</th>
            <th class="p-3">주소</th>
          </tr>
        </thead>

        <tbody>
          <tr v-for="c in filteredCompanies" :key="c.id"
            class="border-t hover:bg-gray-50">

            <td class="p-3 font-semibold">{{ c.name }}</td>
            <td class="p-3">{{ c.phone }}</td>
            <td class="p-3">{{ c.fax }}</td>
            <td class="p-3">{{ c.address }}</td>

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
