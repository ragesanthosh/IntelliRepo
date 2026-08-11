import { Outlet } from 'react-router-dom';
import Navbar from '../components/Navbar';

export default function AppLayout() {
  return (
    <div className="min-h-screen bg-slate-50 dark:bg-neutral-950">
      <Navbar />
      <main className="layout-container py-6 sm:py-8">
        <Outlet />
      </main>
    </div>
  );
}
