<template>
  <div class="max-w-md mx-auto mt-10 bg-white rounded-xl shadow p-6">
    <h2 class="text-xl font-bold mb-4">로그인</h2>

    <div class="mb-3">
      <label class="block text-sm font-medium mb-1">아이디</label>
      <input v-model="username" class="w-full border rounded px-3 py-2" placeholder="아이디" />
    </div>

    <div class="mb-4">
      <label class="block text-sm font-medium mb-1">비밀번호</label>
      <input v-model="password" type="password" class="w-full border rounded px-3 py-2" placeholder="비밀번호" />
    </div>

    <p v-if="error" class="text-red-600 text-sm mb-3">{{ error }}</p>

    <div class="flex gap-2">
      <button
        class="bg-blue-600 text-white px-4 py-2 rounded font-medium"
        @click="handleLogin"
      >
        로그인
      </button>
      <button
        class="bg-gray-200 text-gray-800 px-4 py-2 rounded font-medium"
        @click="handleRegister"
      >
        회원가입
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import api from "../api";

const router = useRouter();
const username = ref("");
const password = ref("");
const error = ref("");

const handleLogin = async () => {
  error.value = "";
  try {
    const res = await api.post("/auth/login", {
      username: username.value,
      password: password.value
    });
    localStorage.setItem("access_token", res.data.access_token);
    router.push("/");
  } catch (e) {
    error.value = "아이디 또는 비밀번호가 올바르지 않습니다.";
  }
};

const handleRegister = async () => {
  error.value = "";
  try {
    await api.post("/auth/register", {
      username: username.value,
      password: password.value
    });
    await handleLogin();
  } catch (e) {
    if (e.response?.status === 409) {
      error.value = "이미 존재하는 아이디입니다.";
    } else {
      error.value = "회원가입에 실패했습니다.";
    }
  }
};
</script>
