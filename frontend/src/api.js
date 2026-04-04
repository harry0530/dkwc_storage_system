import axios from "axios";

const api = axios.create({
  baseURL: "https://dkwc-storage-system.onrender.com"
});

export default api;