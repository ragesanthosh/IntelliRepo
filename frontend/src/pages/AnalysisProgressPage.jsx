import { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { repositoryAPI } from '../services/api';
import ErrorAlert from '../components/ErrorAlert';
import { ANALYSIS_STEPS, getErrorMessage } from '../utils/helpers';

export default function AnalysisProgressPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const url = location.state?.url;
  const [currentStep, setCurrentStep] = useState(0);
  const [error, setError] = useState('');
  const [completed, setCompleted] = useState(false);

  useEffect(() => {
    if (!url) {
      navigate('/dashboard');
      return;
    }

    let stepInterval;
    let cancelled = false;

    const runAnalysis = async () => {
      stepInterval = setInterval(() => {
        setCurrentStep((prev) => {
          if (prev < ANALYSIS_STEPS.length - 2) return prev + 1;
          return prev;
        });
      }, 3000);

      try {
        const { data } = await repositoryAPI.analyze(url);
        if (cancelled) return;

        clearInterval(stepInterval);
        setCurrentStep(ANALYSIS_STEPS.length - 1);
        setCompleted(true);

        setTimeout(() => {
          navigate(`/repository/${data.id}`);
        }, 800);
      } catch (err) {
        if (cancelled) return;
        clearInterval(stepInterval);
        setError(getErrorMessage(err));
      }
    };

    runAnalysis();

    return () => {
      cancelled = true;
      if (stepInterval) clearInterval(stepInterval);
    };
  }, [url, navigate]);

  const progress = completed
    ? 100
    : Math.round(((currentStep + 0.5) / ANALYSIS_STEPS.length) * 100);

  return (
    <div className="py-16 flex justify-center">
      <div className="w-full max-w-xl bg-white dark:bg-neutral-900 rounded-xl border border-slate-200 dark:border-neutral-800 shadow-sm p-8">
        <div className="text-center mb-8">
          <div className="w-14 h-14 bg-blue-50 dark:bg-neutral-800 rounded-2xl flex items-center justify-center mx-auto mb-4">
            {!error && !completed && (
              <div className="w-7 h-7 border-2 border-slate-700 dark:border-indigo-500 border-t-transparent rounded-full animate-spin" />
            )}
            {completed && (
              <svg className="w-7 h-7 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            )}
            {error && (
              <svg className="w-7 h-7 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            )}
          </div>
          <h1 className="text-xl font-semibold text-slate-900 dark:text-neutral-100">
            {error ? 'Analysis Failed' : completed ? 'Analysis Complete' : 'Analyzing Repository'}
          </h1>
          {url && (
            <p className="text-sm text-slate-500 dark:text-neutral-400 mt-1 truncate">{url}</p>
          )}
        </div>

        {!error && (
          <>
            <div className="w-full bg-slate-100 dark:bg-neutral-800 rounded-full h-2 mb-8">
              <div
                className="bg-slate-800 dark:bg-indigo-600 h-2 rounded-full transition-all duration-700 ease-out"
                style={{ width: `${progress}%` }}
              />
            </div>

            <div className="space-y-3">
              {ANALYSIS_STEPS.map((step, index) => {
                const isDone = index < currentStep || completed;
                const isActive = index === currentStep && !completed;

                return (
                  <div key={step.key} className="flex items-center gap-3">
                    <div className={`w-5 h-5 rounded-full flex items-center justify-center shrink-0 transition-colors ${
                      isDone ? 'bg-green-100 dark:bg-green-950 text-green-600' :
                      isActive ? 'bg-slate-200 dark:bg-neutral-700 text-slate-700 dark:text-neutral-200' :
                      'bg-slate-100 dark:bg-neutral-800 text-slate-400'
                    }`}>
                      {isDone ? (
                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                        </svg>
                      ) : isActive ? (
                        <div className="w-2 h-2 bg-slate-700 dark:bg-indigo-400 rounded-full animate-pulse" />
                      ) : (
                        <div className="w-1.5 h-1.5 bg-slate-300 dark:bg-slate-600 rounded-full" />
                      )}
                    </div>
                    <span className={`text-sm ${
                      isDone ? 'text-slate-700 dark:text-neutral-300' :
                      isActive ? 'text-slate-900 dark:text-neutral-100 font-medium' :
                      'text-slate-400 dark:text-neutral-500'
                    }`}>
                      {step.label}
                    </span>
                  </div>
                );
              })}
            </div>
          </>
        )}

        {error && (
          <div className="space-y-4">
            <ErrorAlert message={error} />
            <button
              onClick={() => navigate('/dashboard')}
              className="w-full bg-slate-100 dark:bg-neutral-800 hover:bg-slate-200 dark:hover:bg-neutral-700 text-slate-700 dark:text-neutral-200 font-medium py-2.5 rounded-lg text-sm transition-colors"
            >
              Back to Dashboard
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
