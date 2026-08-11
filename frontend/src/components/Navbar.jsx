import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import ThemeToggle from './ThemeToggle';

export default function Navbar() {
  const { user, logout } = useAuth();

  return (
    <nav className="sticky top-0 z-50 border-b border-slate-200/70 dark:border-neutral-800/80 bg-white/75 dark:bg-neutral-900/85 backdrop-blur-md supports-[backdrop-filter]:bg-white/60 dark:supports-[backdrop-filter]:bg-neutral-900/70">
      <div className="layout-container h-14 flex items-center justify-between">
        <Link to="/dashboard" className="flex items-center gap-2.5 group">
          <div className="w-8 h-8 bg-slate-800 dark:bg-indigo-600 rounded-lg flex items-center justify-center shadow-sm transition-transform duration-200 group-hover:scale-105">
            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
            </svg>
          </div>
          <span className="font-semibold text-slate-900 dark:text-neutral-100 group-hover:text-slate-600 dark:group-hover:text-neutral-300 transition-colors">
            IntelliRepo
          </span>
        </Link>

        <div className="flex items-center gap-2 sm:gap-4">
          <ThemeToggle />
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 bg-slate-100 dark:bg-neutral-800 rounded-full flex items-center justify-center ring-1 ring-slate-200 dark:ring-neutral-700">
              <span className="text-xs font-medium text-slate-600 dark:text-neutral-300">
                {user?.name?.charAt(0)?.toUpperCase() || 'U'}
              </span>
            </div>
            <span className="text-sm text-slate-700 dark:text-neutral-300 hidden sm:block">{user?.name}</span>
          </div>
          <button
            onClick={logout}
            className="text-sm text-slate-500 dark:text-neutral-400 hover:text-slate-800 dark:hover:text-neutral-200 transition-colors duration-200 px-2 py-1 rounded-md hover:bg-slate-100 dark:hover:bg-neutral-800"
          >
            Logout
          </button>
        </div>
      </div>
    </nav>
  );
}
