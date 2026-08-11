import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { repositoryAPI } from '../services/api';
import ErrorAlert from '../components/ErrorAlert';
import { formatDate, isValidGitHubUrl } from '../utils/helpers';

export default function DashboardPage() {
  const [url, setUrl] = useState('');
  const [repositories, setRepositories] = useState([]);
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    loadRepositories();
  }, []);

  const loadRepositories = async () => {
    try {
      const { data } = await repositoryAPI.list();
      setRepositories(data);
    } catch {
      // silently fail on initial load
    } finally {
      setFetching(false);
    }
  };

  const handleAnalyze = async (e) => {
    e.preventDefault();
    setError('');

    const trimmed = url.trim();
    if (!trimmed) {
      setError('Please enter a GitHub repository URL.');
      return;
    }
    if (!isValidGitHubUrl(trimmed)) {
      setError('Please enter a valid GitHub URL (e.g., https://github.com/owner/repo).');
      return;
    }

    setLoading(true);
    navigate('/analyze', { state: { url: trimmed } });
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-neutral-100">Dashboard</h1>
        <p className="text-slate-500 dark:text-neutral-400 mt-1 text-sm">
          Paste a GitHub repository URL to get an AI-powered analysis.
        </p>
      </div>

      <div className="bg-white dark:bg-neutral-900 rounded-xl border border-slate-200 dark:border-neutral-800 shadow-sm p-6 card-interactive">
        <form onSubmit={handleAnalyze} className="space-y-4">
          <div>
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="Paste GitHub Repository URL..."
              disabled={loading}
              className="w-full px-4 py-3.5 input-modern text-sm text-slate-900 dark:text-neutral-100 placeholder:text-slate-400 dark:placeholder:text-neutral-500 disabled:bg-slate-50 dark:disabled:bg-neutral-800 disabled:opacity-60"
            />
          </div>

          {error && <ErrorAlert message={error} onDismiss={() => setError('')} />}

          <button
            type="submit"
            disabled={loading}
            className="btn-primary px-6 py-2.5 rounded-lg text-sm"
          >
            {loading && (
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            )}
            Analyze
          </button>
        </form>
      </div>

      <div>
        <h2 className="text-lg font-semibold text-slate-900 dark:text-neutral-100 mb-4">Recently Analyzed</h2>

        {fetching ? (
          <div className="flex justify-center py-12">
            <div className="w-6 h-6 border-2 border-slate-700 dark:border-indigo-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : repositories.length === 0 ? (
          <div className="bg-white dark:bg-neutral-900 rounded-xl border border-slate-200 dark:border-neutral-800 border-dashed p-12 text-center">
            <div className="w-12 h-12 bg-slate-100 dark:bg-neutral-800 rounded-xl flex items-center justify-center mx-auto mb-3">
              <svg className="w-6 h-6 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
              </svg>
            </div>
            <p className="text-slate-500 dark:text-neutral-400 text-sm">No repositories analyzed yet.</p>
            <p className="text-slate-400 dark:text-neutral-500 text-xs mt-1">Paste a URL above to get started.</p>
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {repositories.map((repo) => (
              <button
                key={repo.id}
                onClick={() => navigate(`/repository/${repo.id}`)}
                className="bg-white dark:bg-neutral-900 rounded-xl border border-slate-200 dark:border-neutral-800 shadow-sm p-4 text-left card-interactive group"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-medium text-slate-900 dark:text-neutral-100 group-hover:text-slate-600 dark:group-hover:text-neutral-200 transition-colors duration-200 truncate">
                      {repo.repository_name}
                    </p>
                    <p className="text-sm text-slate-500 dark:text-neutral-400 mt-0.5">{repo.owner}</p>
                  </div>
                  <svg className="w-4 h-4 text-slate-300 dark:text-neutral-600 group-hover:text-slate-500 dark:group-hover:text-neutral-400 shrink-0 mt-1 transition-colors duration-200" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </div>
                <p className="text-xs text-slate-400 dark:text-neutral-500 mt-2">{formatDate(repo.created_at)}</p>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
