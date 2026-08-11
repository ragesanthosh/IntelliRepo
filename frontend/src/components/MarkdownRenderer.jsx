import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { useTheme } from '../context/ThemeContext';

export default function MarkdownRenderer({ content }) {
  const { isDark } = useTheme();
  if (!content) return null;

  const parts = content.split(/(```[\s\S]*?```)/g);

  return (
    <div className="markdown-body text-slate-700 dark:text-neutral-300 text-[15px] leading-relaxed">
      {parts.map((part, i) => {
        const codeMatch = part.match(/^```(\w*)\n?([\s\S]*?)```$/);
        if (codeMatch) {
          const [, lang, code] = codeMatch;
          return (
            <SyntaxHighlighter
              key={i}
              language={lang || 'text'}
              style={isDark ? oneDark : oneLight}
              customStyle={{
                margin: '1em 0',
                borderRadius: '8px',
                fontSize: '13px',
                border: isDark ? '1px solid #404040' : '1px solid #e2e8f0',
              }}
            >
              {code.trim()}
            </SyntaxHighlighter>
          );
        }

        return <InlineMarkdown key={i} text={part} />;
      })}
    </div>
  );
}

function InlineMarkdown({ text }) {
  if (!text.trim()) return null;

  const lines = text.split('\n');
  const elements = [];
  let listItems = [];
  let listType = null;

  const flushList = () => {
    if (listItems.length > 0) {
      const Tag = listType === 'ol' ? 'ol' : 'ul';
      elements.push(
        <Tag key={`list-${elements.length}`} className="mb-3 pl-5 space-y-1">
          {listItems.map((item, j) => (
            <li key={j}>{formatInline(item)}</li>
          ))}
        </Tag>
      );
      listItems = [];
      listType = null;
    }
  };

  lines.forEach((line, idx) => {
    const trimmed = line.trim();

    if (trimmed.startsWith('### ')) {
      flushList();
      elements.push(<h3 key={idx} className="text-base font-semibold mt-4 mb-2 dark:text-slate-100">{formatInline(trimmed.slice(4))}</h3>);
    } else if (trimmed.startsWith('## ')) {
      flushList();
      elements.push(<h2 key={idx} className="text-lg font-semibold mt-4 mb-2 dark:text-slate-100">{formatInline(trimmed.slice(3))}</h2>);
    } else if (trimmed.startsWith('# ')) {
      flushList();
      elements.push(<h1 key={idx} className="text-xl font-semibold mt-4 mb-2 dark:text-slate-100">{formatInline(trimmed.slice(2))}</h1>);
    } else if (trimmed.match(/^[-*] /)) {
      if (listType !== 'ul') { flushList(); listType = 'ul'; }
      listItems.push(trimmed.slice(2));
    } else if (trimmed.match(/^\d+\. /)) {
      if (listType !== 'ol') { flushList(); listType = 'ol'; }
      listItems.push(trimmed.replace(/^\d+\. /, ''));
    } else if (trimmed.startsWith('> ')) {
      flushList();
      elements.push(
        <blockquote key={idx} className="border-l-3 border-slate-200 dark:border-slate-600 pl-4 text-slate-500 dark:text-slate-400 my-2">
          {formatInline(trimmed.slice(2))}
        </blockquote>
      );
    } else if (trimmed === '') {
      flushList();
    } else {
      flushList();
      elements.push(<p key={idx} className="mb-2">{formatInline(trimmed)}</p>);
    }
  });

  flushList();
  return <>{elements}</>;
}

function formatInline(text) {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith('`') && part.endsWith('`')) {
      return <code key={i} className="bg-slate-100 dark:bg-neutral-800 px-1.5 py-0.5 rounded text-sm font-mono">{part.slice(1, -1)}</code>;
    }
    const linkMatch = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
    if (linkMatch) {
      return <a key={i} href={linkMatch[2]} className="text-indigo-700 dark:text-indigo-400 hover:underline" target="_blank" rel="noopener noreferrer">{linkMatch[1]}</a>;
    }
    return part;
  });
}
