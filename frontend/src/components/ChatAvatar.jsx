export default function ChatAvatar({ role, userName }) {
  if (role === 'user') {
    const initial = userName?.charAt(0)?.toUpperCase() || 'U';
    return (
      <div
        className="w-8 h-8 rounded-full bg-slate-600 dark:bg-neutral-700 ring-2 ring-white dark:ring-neutral-900 flex items-center justify-center shrink-0"
        aria-hidden="true"
      >
        <span className="text-xs font-semibold text-white">{initial}</span>
      </div>
    );
  }

  return (
    <div
      className="w-8 h-8 rounded-full bg-indigo-700 dark:bg-indigo-600 ring-2 ring-white dark:ring-neutral-900 flex items-center justify-center shrink-0"
      aria-label="IntelliAI"
    >
      <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
      </svg>
    </div>
  );
}
