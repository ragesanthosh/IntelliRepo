import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { repositoryAPI } from '../services/api';
import SectionCard from '../components/SectionCard';
import MarkdownRenderer from '../components/MarkdownRenderer';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorAlert from '../components/ErrorAlert';
import { getErrorMessage } from '../utils/helpers';

const sectionIcons = {
  summary: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  workflow: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
    </svg>
  ),
  architecture: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
    </svg>
  ),
  files: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  ),
  tech: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
    </svg>
  ),
  insights: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
    </svg>
  ),
};

export default function RepositoryOverviewPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [repo, setRepo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadRepository();
  }, [id]);

  const loadRepository = async () => {
    try {
      const { data } = await repositoryAPI.get(id);
      setRepo(data);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-24">
        <LoadingSpinner text="Loading repository analysis..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-lg mx-auto py-16 space-y-4">
        <ErrorAlert message={error} />
        <button onClick={() => navigate('/dashboard')} className="text-sm text-indigo-700 dark:text-indigo-400 hover:underline transition-colors duration-200">
          Back to Dashboard
        </button>
      </div>
    );
  }

  const summary = repo?.summary || {};

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <button
            onClick={() => navigate('/dashboard')}
            className="text-sm text-slate-500 dark:text-neutral-400 hover:text-slate-700 dark:hover:text-neutral-200 mb-2 flex items-center gap-1"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Dashboard
          </button>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-neutral-100">{repo.repository_name}</h1>
          <p className="text-slate-500 dark:text-neutral-400 text-sm mt-0.5">
            by{' '}
            <a
              href={repo.repository_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-indigo-700 dark:text-indigo-400 hover:underline transition-colors duration-200"
            >
              {repo.owner}
            </a>
          </p>
        </div>
        <Link
          to={`/repository/${id}/chat`}
          className="inline-flex items-center gap-2 btn-primary px-4 py-2.5 rounded-lg text-sm shrink-0"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          Chat with IntelliAI
        </Link>
      </div>

      {/* Section 1: Project Summary */}
      <SectionCard title="Project Summary" icon={sectionIcons.summary}>
        <MarkdownRenderer content={summary.project_summary} />
      </SectionCard>

      {/* Section 2: How This Project Works */}
      <SectionCard title="How This Project Works" icon={sectionIcons.workflow}>
        <MarkdownRenderer content={summary.how_it_works} />
      </SectionCard>

      {/* Section 3: Architecture */}
      {summary.architecture && (
        <SectionCard title="Architecture" icon={sectionIcons.architecture}>
          <div className="space-y-5">
            {summary.architecture.folder_structure && (
              <div>
                <h3 className="text-sm font-semibold text-slate-800 dark:text-neutral-200 mb-2">Folder Organization</h3>
                <p className="text-slate-600 dark:text-neutral-300 text-[15px] leading-relaxed">
                  {summary.architecture.folder_structure}
                </p>
              </div>
            )}

            {summary.architecture.main_folders?.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200 mb-3">Main Folders</h3>
                <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                  {summary.architecture.main_folders.map((folder, i) => (
                    <div key={i} className="bg-slate-50 dark:bg-neutral-800 rounded-lg px-4 py-3 border border-slate-100 dark:border-neutral-700">
                      <p className="font-mono text-sm font-medium text-slate-800 dark:text-neutral-200">{folder.name}</p>
                      <p className="text-sm text-slate-500 dark:text-neutral-400 mt-1">{folder.responsibility}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {summary.architecture.important_files?.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200 mb-2">Key Files</h3>
                <div className="flex flex-wrap gap-2">
                  {summary.architecture.important_files.map((file, i) => (
                    <span key={i} className="bg-slate-100 dark:bg-neutral-800 text-slate-700 dark:text-neutral-300 text-xs font-mono px-2.5 py-1 rounded-md">
                      {file}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </SectionCard>
      )}

      {/* Section 4: Important Files */}
      {summary.important_files?.length > 0 && (
        <SectionCard title="Important Files" icon={sectionIcons.files}>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {summary.important_files.map((file, i) => (
              <div key={i} className="border border-slate-100 dark:border-neutral-700 rounded-lg p-4 card-interactive">
                <p className="font-mono text-sm font-medium text-indigo-700 dark:text-indigo-400">{file.file_name}</p>
                <p className="text-sm font-medium text-slate-800 dark:text-neutral-200 mt-2">{file.purpose}</p>
                <p className="text-xs text-slate-500 dark:text-neutral-400 mt-1">{file.importance}</p>
                <p className="text-sm text-slate-600 dark:text-neutral-300 mt-2 leading-relaxed">{file.explanation}</p>
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {/* Section 5: Technology Stack */}
      {summary.technology_stack?.length > 0 && (
        <SectionCard title="Technology Stack" icon={sectionIcons.tech}>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {summary.technology_stack.map((tech, i) => (
              <div key={i} className="flex gap-3 items-start">
                <div className="w-2 h-2 bg-indigo-600 dark:bg-indigo-400 rounded-full mt-2 shrink-0" />
                <div>
                  <p className="font-medium text-slate-800 dark:text-neutral-200">{tech.name}</p>
                  <p className="text-sm text-slate-500 dark:text-neutral-400 mt-0.5">{tech.reason}</p>
                </div>
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {/* Section 6: AI Insights */}
      {summary.ai_insights && (
        <SectionCard title="AI Insights" icon={sectionIcons.insights}>
          <div className="space-y-5">
            <div className="grid gap-4 sm:grid-cols-2">
              <InsightBadge label="Complexity" value={summary.ai_insights.complexity} />
              <InsightBadge label="Code Quality" value={summary.ai_insights.code_quality} />
            </div>

            <InsightList title="Strengths" items={summary.ai_insights.strengths} color="green" />
            <InsightList title="Weaknesses" items={summary.ai_insights.weaknesses} color="amber" />
            <InsightList title="Possible Improvements" items={summary.ai_insights.improvements} color="blue" />
          </div>
        </SectionCard>
      )}
    </div>
  );
}

function InsightBadge({ label, value }) {
  return (
    <div className="bg-slate-50 dark:bg-neutral-800 rounded-lg px-4 py-3 border border-slate-100 dark:border-neutral-700">
      <p className="text-xs font-medium text-slate-500 dark:text-neutral-400 uppercase tracking-wide">{label}</p>
      <p className="text-sm text-slate-800 dark:text-neutral-200 mt-1">{value}</p>
    </div>
  );
}

function InsightList({ title, items, color }) {
  if (!items?.length) return null;

  const dotColors = { green: 'bg-green-500', amber: 'bg-amber-500', blue: 'bg-blue-500' };

  return (
    <div>
      <h3 className="text-sm font-semibold text-slate-800 dark:text-neutral-200 mb-2">{title}</h3>
      <ul className="space-y-1.5">
        {items.map((item, i) => (
          <li key={i} className="flex gap-2 items-start text-sm text-slate-600 dark:text-neutral-300">
            <span className={`w-1.5 h-1.5 rounded-full ${dotColors[color]} mt-2 shrink-0`} />
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}
