<template>
  <div class="max-w-md mx-auto mt-10 bg-white rounded-xl shadow p-6">
    <h2 class="text-xl font-bold mb-4">로그인</h2>

    <div class="mb-3">
      <label class="block text-sm font-medium mb-1">아이디(이메일)</label>
      <input v-model="username" class="w-full border rounded px-3 py-2" placeholder="아이디(이메일)" />
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
    </div>

    <p class="text-xs text-gray-500 mt-3">
      계정 생성은 관리자에게 요청하세요.
    </p>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { signInWithEmailAndPassword } from "firebase/auth";
import { auth } from "../firebase";

const router = useRouter();
const username = ref("");
const password = ref("");
const error = ref("");

const handleLogin = async () => {
  error.value = "";
  try {
    await signInWithEmailAndPassword(auth, username.value, password.value);
    router.push("/");
  } catch (e) {
    error.value = "로그인에 실패했습니다. 아이디/비밀번호를 확인하세요.";
  }
};
</script>
