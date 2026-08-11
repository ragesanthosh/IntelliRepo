import { useState, useEffect, useRef } from 'react';
import { formatDate } from '../utils/helpers';

export default function ConversationSidebar({
  conversations,
  activeId,
  onSelect,
  onNew,
  onRename,
  onDelete,
  creating,
}) {
  return (
    <aside className="w-full lg:w-72 xl:w-80 shrink-0 flex flex-col bg-white dark:bg-neutral-900 border border-slate-200 dark:border-neutral-800 rounded-xl shadow-sm overflow-hidden lg:max-h-full max-h-52 card-interactive">
      <div className="p-3 border-b border-slate-100 dark:border-neutral-800">
        <button
          onClick={onNew}
          disabled={creating}
          className="w-full flex items-center justify-center gap-2 btn-primary py-2.5 px-3 rounded-lg text-sm"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          {creating ? 'Creating...' : 'New Chat'}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1 min-h-0">
        {conversations.length === 0 ? (
          <p className="text-xs text-slate-400 dark:text-neutral-500 text-center py-6 px-2">
            No conversations yet
          </p>
        ) : (
          conversations.map((conv) => (
            <ConversationItem
              key={conv.id}
              conversation={conv}
              isActive={conv.id === activeId}
              onSelect={() => onSelect(conv.id)}
              onRename={(title) => onRename(conv.id, title)}
              onDelete={() => onDelete(conv.id)}
            />
          ))
        )}
      </div>
    </aside>
  );
}

function ConversationItem({ conversation, isActive, onSelect, onRename, onDelete }) {
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(conversation.title);
  const inputRef = useRef(null);

  useEffect(() => {
    setTitle(conversation.title);
  }, [conversation.title]);

  useEffect(() => {
    if (editing) inputRef.current?.focus();
  }, [editing]);

  const submitRename = () => {
    const trimmed = title.trim();
    if (trimmed && trimmed !== conversation.title) {
      onRename(trimmed);
    } else {
      setTitle(conversation.title);
    }
    setEditing(false);
  };

  const handleDelete = (e) => {
    e.stopPropagation();
    if (window.confirm(`Delete "${conversation.title}"? This cannot be undone.`)) {
      onDelete();
    }
  };

  return (
    <div
      onClick={onSelect}
      className={`group relative rounded-lg px-3 py-2.5 cursor-pointer transition-all duration-200 ${
        isActive
          ? 'bg-slate-100 dark:bg-neutral-800 border border-slate-200 dark:border-neutral-600 shadow-sm'
          : 'hover:bg-slate-50 dark:hover:bg-neutral-800/80 border border-transparent hover:border-slate-200 dark:hover:border-neutral-700'
      }`}
    >
      {editing ? (
        <input
          ref={inputRef}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onBlur={submitRename}
          onKeyDown={(e) => {
            if (e.key === 'Enter') submitRename();
            if (e.key === 'Escape') {
              setTitle(conversation.title);
              setEditing(false);
            }
          }}
          onClick={(e) => e.stopPropagation()}
          className="w-full text-sm input-modern py-1.5 px-2 text-slate-900 dark:text-neutral-100"
        />
      ) : (
        <>
          <p className={`text-sm font-medium truncate pr-12 ${
            isActive ? 'text-slate-900 dark:text-neutral-100' : 'text-slate-700 dark:text-neutral-300'
          }`}>
            {conversation.title}
          </p>
          <p className="text-xs text-slate-400 dark:text-neutral-500 mt-0.5">
            {formatDate(conversation.updated_at)}
            {conversation.message_count > 0 && ` · ${conversation.message_count} msgs`}
          </p>
          <div className="absolute right-2 top-2 flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={(e) => { e.stopPropagation(); setEditing(true); }}
              className="p-1 rounded text-slate-400 hover:text-slate-600 dark:hover:text-neutral-200 hover:bg-slate-200 dark:hover:bg-neutral-700"
              title="Rename"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
              </svg>
            </button>
            <button
              onClick={handleDelete}
              className="p-1 rounded text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/50"
              title="Delete"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        </>
      )}
    </div>
  );
}
