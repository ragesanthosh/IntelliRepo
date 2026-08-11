import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { chatAPI, repositoryAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import ConversationSidebar from '../components/ConversationSidebar';
import ChatAvatar from '../components/ChatAvatar';
import MarkdownRenderer from '../components/MarkdownRenderer';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorAlert from '../components/ErrorAlert';
import { SUGGESTED_QUESTIONS, getErrorMessage } from '../utils/helpers';

export default function ChatPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [repo, setRepo] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [pageLoading, setPageLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [switching, setSwitching] = useState(false);
  const [error, setError] = useState('');
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const loadConversation = useCallback(async (conversationId) => {
    setSwitching(true);
    setError('');
    try {
      const { data } = await chatAPI.getConversation(id, conversationId);
      setMessages(
        (data.messages || []).map((m) => ({
          role: m.role,
          content: m.content,
          sources: m.sources || [],
        }))
      );
      setActiveConversationId(conversationId);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSwitching(false);
    }
  }, [id]);

  const loadConversations = useCallback(async (selectId = null) => {
    const { data } = await chatAPI.listConversations(id);
    setConversations(data);

    if (data.length === 0) {
      const { data: created } = await chatAPI.createConversation(id);
      setConversations([{
        id: created.id,
        title: created.title,
        message_count: 0,
        created_at: created.created_at,
        updated_at: created.updated_at,
      }]);
      setActiveConversationId(created.id);
      setMessages([]);
      return created.id;
    }

    const targetId = selectId && data.find((c) => c.id === selectId)
      ? selectId
      : data[0].id;

    await loadConversation(targetId);
    return targetId;
  }, [id, loadConversation]);

  useEffect(() => {
    const init = async () => {
      try {
        const { data: repoData } = await repositoryAPI.get(id);
        setRepo(repoData);
        await loadConversations();
      } catch (err) {
        setError(getErrorMessage(err));
      } finally {
        setPageLoading(false);
      }
    };
    init();
  }, [id, loadConversations]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleNewChat = async () => {
    setCreating(true);
    setError('');
    try {
      const { data } = await chatAPI.createConversation(id);
      const newItem = {
        id: data.id,
        title: data.title,
        message_count: 0,
        created_at: data.created_at,
        updated_at: data.updated_at,
      };
      setConversations((prev) => [newItem, ...prev]);
      setActiveConversationId(data.id);
      setMessages([]);
      inputRef.current?.focus();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setCreating(false);
    }
  };

  const handleSelectConversation = async (conversationId) => {
    if (conversationId === activeConversationId || switching) return;
    await loadConversation(conversationId);
  };

  const handleRename = async (conversationId, title) => {
    try {
      const { data } = await chatAPI.renameConversation(id, conversationId, title);
      setConversations((prev) =>
        prev.map((c) => (c.id === conversationId ? { ...c, title: data.title } : c))
      );
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const handleDelete = async (conversationId) => {
    try {
      await chatAPI.deleteConversation(id, conversationId);
      const remaining = conversations.filter((c) => c.id !== conversationId);
      setConversations(remaining);

      if (conversationId === activeConversationId) {
        if (remaining.length > 0) {
          await loadConversation(remaining[0].id);
        } else {
          setCreating(true);
          try {
            const { data } = await chatAPI.createConversation(id);
            const newItem = {
              id: data.id,
              title: data.title,
              message_count: 0,
              created_at: data.created_at,
              updated_at: data.updated_at,
            };
            setConversations([newItem]);
            setActiveConversationId(data.id);
            setMessages([]);
          } catch (err) {
            setError(getErrorMessage(err));
          } finally {
            setCreating(false);
          }
        }
      }
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const sendMessage = async (text) => {
    const message = text.trim();
    if (!message || loading || !activeConversationId) return;

    setInput('');
    setError('');

    const userMessage = { role: 'user', content: message };
    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    try {
      const { data } = await chatAPI.send(id, activeConversationId, message);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.answer,
          sources: data.sources || [],
        },
      ]);

      setConversations((prev) => {
        const updated = prev.map((c) => {
          if (c.id !== activeConversationId) return c;
          return {
            ...c,
            title: data.title || c.title,
            message_count: c.message_count + 2,
            updated_at: new Date().toISOString(),
          };
        });
        const active = updated.find((c) => c.id === activeConversationId);
        const rest = updated.filter((c) => c.id !== activeConversationId);
        return active ? [active, ...rest] : updated;
      });
    } catch (err) {
      setError(getErrorMessage(err));
      setMessages((prev) => prev.slice(0, -1));
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    sendMessage(input);
  };

  const activeConversation = conversations.find((c) => c.id === activeConversationId);

  if (pageLoading) {
    return (
      <div className="flex justify-center py-24">
        <LoadingSpinner text="Loading IntelliAI..." />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-7rem)] w-full">
      <div className="flex items-center justify-between mb-4 shrink-0">
        <div>
          <button
            onClick={() => navigate(`/repository/${id}`)}
            className="text-sm text-slate-500 dark:text-neutral-400 hover:text-slate-700 dark:hover:text-neutral-200 mb-1 flex items-center gap-1"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Overview
          </button>
          <h1 className="text-lg font-semibold text-slate-900 dark:text-neutral-100">
            IntelliAI — {repo?.repository_name}
          </h1>
          {activeConversation && (
            <p className="text-sm text-slate-500 dark:text-neutral-400 mt-0.5 truncate">
              {activeConversation.title}
            </p>
          )}
        </div>
      </div>

      <div className="flex flex-col lg:flex-row gap-4 flex-1 min-h-0">
        <ConversationSidebar
          conversations={conversations}
          activeId={activeConversationId}
          onSelect={handleSelectConversation}
          onNew={handleNewChat}
          onRename={handleRename}
          onDelete={handleDelete}
          creating={creating}
        />

        <div className="flex-1 flex flex-col min-w-0 min-h-0">
          <div className="flex-1 overflow-y-auto bg-white dark:bg-neutral-900 rounded-xl border border-slate-200 dark:border-neutral-800 shadow-sm relative card-interactive">
            {switching && (
              <div className="absolute inset-0 bg-white/60 dark:bg-neutral-900/60 flex items-center justify-center z-10 rounded-xl">
                <LoadingSpinner size="sm" />
              </div>
            )}

            {messages.length === 0 && !switching ? (
              <div className="flex flex-col items-center justify-center h-full p-8 text-center">
                <div className="mb-4">
                  <ChatAvatar role="assistant" />
                </div>
                <p className="text-slate-700 dark:text-neutral-200 font-medium mb-1">Ask IntelliAI anything</p>
                <p className="text-sm text-slate-500 dark:text-neutral-400 mb-6 max-w-sm">
                  Each conversation has its own history and IntelliAI context. Previous chats are never deleted unless you remove them.
                </p>
                <div className="flex flex-wrap gap-2 justify-center max-w-md">
                  {SUGGESTED_QUESTIONS.map((q) => (
                    <button
                      key={q}
                      onClick={() => sendMessage(q)}
                      className="text-sm bg-slate-50 dark:bg-neutral-800 hover:bg-slate-100 dark:hover:bg-neutral-700 text-slate-600 dark:text-neutral-300 px-3 py-1.5 rounded-full border border-slate-200 dark:border-neutral-700 transition-all duration-200 hover:shadow-sm"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="p-4 sm:p-6 space-y-6">
                {messages.map((msg, i) => (
                  <div
                    key={i}
                    className={`flex gap-3 animate-fade-in ${
                      msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'
                    }`}
                  >
                    <ChatAvatar role={msg.role === 'user' ? 'user' : 'assistant'} userName={user?.name} />
                    <div className={`max-w-[80%] min-w-0 px-4 py-3 ${
                      msg.role === 'user' ? 'bubble-user' : 'bubble-assistant'
                    }`}>
                      {msg.role === 'user' ? (
                        <p className="text-sm leading-relaxed">{msg.content}</p>
                      ) : (
                        <>
                          <MarkdownRenderer content={msg.content} />
                          {Array.isArray(msg.sources) && msg.sources.length > 0 && (
                            <div className="mt-3 pt-3 border-t border-slate-100 dark:border-neutral-800">
                              <p className="text-xs font-medium text-slate-500 dark:text-neutral-400 mb-1.5">
                                Sources
                              </p>
                              <ul className="space-y-1">
                                {msg.sources.map((src) => (
                                  <li
                                    key={src}
                                    className="text-xs text-slate-600 dark:text-neutral-300 font-mono truncate"
                                    title={src}
                                  >
                                    {src}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  </div>
                ))}

                {loading && (
                  <div className="flex gap-3 animate-fade-in">
                    <ChatAvatar role="assistant" />
                    <div className="bubble-assistant px-4 py-3 flex flex-col gap-1">
                      <div className="flex items-center gap-1.5">
                        <span className="typing-dot w-2 h-2 bg-slate-400 dark:bg-neutral-500 rounded-full inline-block" />
                        <span className="typing-dot w-2 h-2 bg-slate-400 dark:bg-neutral-500 rounded-full inline-block" />
                        <span className="typing-dot w-2 h-2 bg-slate-400 dark:bg-neutral-500 rounded-full inline-block" />
                      </div>
                      <p className="text-xs text-slate-400 dark:text-neutral-500">
                        Searching repository context…
                      </p>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            )}
          </div>

          <div className="mt-4 shrink-0 space-y-2">
            {error && <ErrorAlert message={error} onDismiss={() => setError('')} />}

            <form onSubmit={handleSubmit} className="flex gap-2 items-center">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Message IntelliAI about this repository..."
                disabled={loading || !activeConversationId}
                className="flex-1 px-5 py-3.5 input-modern text-sm text-slate-900 dark:text-neutral-100 placeholder:text-slate-400 dark:placeholder:text-neutral-500 disabled:opacity-60"
              />
              <button
                type="submit"
                disabled={loading || !input.trim() || !activeConversationId}
                className="btn-primary px-4 py-3.5 rounded-2xl shrink-0"
                aria-label="Send message"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
