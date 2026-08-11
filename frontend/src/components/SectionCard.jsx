export default function SectionCard({ title, children, icon }) {
  return (
    <section className="bg-white dark:bg-neutral-900 rounded-xl border border-slate-200 dark:border-neutral-800 shadow-sm overflow-hidden animate-fade-in card-interactive">
      <div className="px-6 py-4 border-b border-slate-100 dark:border-neutral-800 flex items-center gap-3">
        {icon && (
          <div className="w-8 h-8 bg-slate-100 dark:bg-neutral-800 rounded-lg flex items-center justify-center text-slate-600 dark:text-neutral-300">
            {icon}
          </div>
        )}
        <h2 className="text-lg font-semibold text-slate-900 dark:text-neutral-100">{title}</h2>
      </div>
      <div className="px-6 py-5">{children}</div>
    </section>
  );
}
