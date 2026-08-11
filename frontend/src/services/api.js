import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export const authAPI = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
  me: () => api.get('/auth/me'),
};

export const repositoryAPI = {
  analyze: (url) => api.post('/repository/analyze', { url }),
  list: () => api.get('/repository'),
  get: (id) => api.get(`/repository/${id}`),
};

export const chatAPI = {
  listConversations: (repositoryId) => api.get(`/chat/${repositoryId}/conversations`),
  createConversation: (repositoryId) => api.post(`/chat/${repositoryId}/conversations`),
  getConversation: (repositoryId, conversationId) =>
    api.get(`/chat/${repositoryId}/conversations/${conversationId}`),
  renameConversation: (repositoryId, conversationId, title) =>
    api.patch(`/chat/${repositoryId}/conversations/${conversationId}`, { title }),
  deleteConversation: (repositoryId, conversationId) =>
    api.delete(`/chat/${repositoryId}/conversations/${conversationId}`),
  send: (repositoryId, conversationId, message) =>
    api.post('/chat/message', {
      repository_id: repositoryId,
      conversation_id: conversationId,
      message,
    }),
};

export default api;
