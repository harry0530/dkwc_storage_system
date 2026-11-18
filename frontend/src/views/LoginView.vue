<template>
  <div class="w-full max-w-md border border-white/20 bg-white p-7 shadow-2xl sm:p-9">
    <p class="eyebrow">Authorized Access</p>
    <h2 class="mb-2 text-2xl font-bold text-slate-900">운영 시스템 로그인</h2>
    <p class="mb-7 text-sm text-slate-500">동광 생산·재고 관리 시스템입니다.</p>

    <form @submit.prevent="handleLogin">
    <div class="mb-3">
      <label class="mb-1.5 block text-xs font-semibold text-slate-600">아이디(이메일)</label>
      <input v-model="username" class="input w-full" autocomplete="username" placeholder="name@dkwc.co.kr" />
    </div>

    <div class="mb-4">
      <label class="mb-1.5 block text-xs font-semibold text-slate-600">비밀번호</label>
      <input v-model="password" type="password" class="input w-full" autocomplete="current-password" placeholder="비밀번호" />
    </div>

    <p v-if="error" class="text-red-600 text-sm mb-3">{{ error }}</p>

    <div>
      <button
        type="submit"
        class="btn btn-primary h-11 w-full"
      >
        로그인
      </button>
    </div>

    <p class="mt-4 text-center text-xs text-slate-400">
      계정 생성은 관리자에게 요청하세요.
    </p>
    </form>
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
