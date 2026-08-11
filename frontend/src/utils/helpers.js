export function formatDate(dateString) {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function isValidGitHubUrl(url) {
  const pattern = /^https?:\/\/github\.com\/[a-zA-Z0-9_.-]+\/[a-zA-Z0-9_.-]+\/?$/;
  return pattern.test(url.trim().replace(/\.git$/, '').replace(/\/$/, ''));
}

export function getErrorMessage(error) {
  if (error.code === 'ECONNABORTED') {
    return 'The request timed out. Repository analysis can take several minutes — please try again.';
  }
  if (error.response?.data?.detail) {
    const detail = error.response.data.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) return detail.map((d) => d.msg).join(', ');
  }
  if (error.message === 'Network Error') {
    return 'Unable to connect to the server. Make sure the backend is running on http://127.0.0.1:8000.';
  }
  return 'Something went wrong. Please try again.';
}

export const SUGGESTED_QUESTIONS = [
  'Explain this project.',
  'How does authentication work?',
  'Explain the folder structure.',
  'Where is the API?',
  'Explain the main workflow.',
  'How to run locally?',
];

export const ANALYSIS_STEPS = [
  { key: 'validating', label: 'Validating Repository' },
  { key: 'cloning', label: 'Cloning Repository' },
  { key: 'reading', label: 'Reading Files' },
  { key: 'embedding', label: 'Creating Embeddings' },
  { key: 'understanding', label: 'Understanding Repository' },
  { key: 'generating', label: 'Generating Summary' },
  { key: 'finishing', label: 'Finishing Analysis' },
];
