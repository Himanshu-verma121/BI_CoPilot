
import axios from "axios";

const BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";


const api = axios.create({
    baseURL: BASE_URL,
    timeout: 30000,
    headers: {
        "Content-Type": "application/json"
    }
});

// Request Interceptor 
api.interceptors.request.use(
    (config) => {

        const token = localStorage.getItem("bi_token");
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Response Interceptor
api.interceptors.response.use(
    (response) => {
        return response;
    },
    (error) => {
        // 401 Unauthorized
        if (error.response?.status === 401) {

            localStorage.removeItem("bi_token");
            localStorage.removeItem("bi_user");
            // Redirect to login page
            window.location.href = "/login";
        }
        return Promise.reject(error);
    }
);

// AUTH API CALLS 
// Register, Login, Get current user
export const authAPI = {

    register: (data) => api.post("/auth/register", data),

    login: (data) => api.post("/auth/login", data),

    getMe: () => api.get("/auth/me"),
};

// CONNECTION API CALLS (Database connection)
export const connectionAPI = {

    // Add new database connection
    add: (data) => api.post("/connections/add", data),

    // Get all connections for current company
    list: () => api.get("/connections/list"),
};

// QUERY API CALLS 
export const queryAPI = {

    // Ask a question to AI
    // data = { question, connection_id }
    ask: (data) => api.post("/query/ask", data),
};

// EXPORT API 
export const exportAPI = {
    download: (data) =>
        api.post("/export/download", data, {
            responseType: "blob",
        }),
};

export default api;
