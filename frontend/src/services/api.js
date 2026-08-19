import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
  timeout: 120000,
  withCredentials: true,
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
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
  logout: () => api.post('/auth/logout'),
  me: () => api.get('/auth/me'),
};

export const repositoryAPI = {
  // Analysis can take several minutes (clone + embed + Gemini)
  analyze: (url) => api.post('/repository/analyze', { url }, { timeout: 600000 }),
  list: () => api.get('/repository'),
  get: (id) => api.get(`/repository/${id}`),
  reindex: (id) => api.post(`/repository/${id}/reindex`, null, { timeout: 600000 }),
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
    api.post(
      '/chat/message',
      {
        repository_id: repositoryId,
        conversation_id: conversationId,
        message,
      },
      { timeout: 180000 }
    ),
};

export default api;
