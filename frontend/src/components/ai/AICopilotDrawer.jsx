// frontend/src/components/ai/AICopilotDrawer.jsx
import React, { useState, useRef, useEffect } from 'react';
import {
  Sparkles,
  X,
  Send,
  Brain,
  Bot,
  User,
  AlertTriangle,
  RefreshCw,
  Terminal,
  ShieldCheck,
  CheckCircle2,
  Trash2,
  HelpCircle,
  Activity,
  Layers,
  Server
} from 'lucide-react';
import { api } from '../../services/api';

function FormattedCopilotMessage({ content }) {
  if (!content) return null;

  // Split lines into structured blocks: tables, headings, dividers, lists, paragraphs
  const lines = content.split('\n');
  const blocks = [];
  let currentTable = null;
  let currentList = null;

  const flushTable = () => {
    if (currentTable) {
      blocks.push({ type: 'table', rows: currentTable });
      currentTable = null;
    }
  };

  const flushList = () => {
    if (currentList) {
      blocks.push({ type: 'list', items: currentList });
      currentList = null;
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

    // Markdown table row
    if (line.startsWith('|') && line.endsWith('|')) {
      flushList();
      const cells = line.split('|').slice(1, -1).map(c => c.trim());
      // Check if divider row like |---|---|
      const isDivider = cells.every(c => /^[-:]+$/.test(c));
      if (!isDivider) {
        if (!currentTable) currentTable = [];
        currentTable.push(cells);
      }
      continue;
    } else {
      flushTable();
    }

    // Horizontal Dividers
    if (line === '---' || line === '***' || line === '___') {
      flushList();
      blocks.push({ type: 'divider' });
      continue;
    }

    // Headings
    if (line.startsWith('#### ')) {
      flushList();
      blocks.push({ type: 'h4', text: line.replace('#### ', '') });
      continue;
    }
    if (line.startsWith('### ')) {
      flushList();
      blocks.push({ type: 'h3', text: line.replace('### ', '') });
      continue;
    }
    if (line.startsWith('## ')) {
      flushList();
      blocks.push({ type: 'h2', text: line.replace('## ', '') });
      continue;
    }

    // List item
    if (line.startsWith('- ') || line.startsWith('* ')) {
      if (!currentList) currentList = [];
      currentList.push(line.substring(2));
      continue;
    } else {
      flushList();
    }

    // Empty lines
    if (!line) {
      continue;
    }

    // Standard paragraph
    blocks.push({ type: 'paragraph', text: line });
  }

  flushTable();
  flushList();

  // Helper to render inline formatting: bold and code chips
  const renderInline = (str) => {
    if (typeof str !== 'string') return str;

    const parts = [];
    let lastIndex = 0;
    const regex = /(\*\*[^*]+\*\*|`[^`]+`)/g;
    let match;

    while ((match = regex.exec(str)) !== null) {
      if (match.index > lastIndex) {
        parts.push(str.substring(lastIndex, match.index));
      }
      const token = match[0];
      if (token.startsWith('**') && token.endsWith('**')) {
        parts.push(
          <strong key={match.index} className="font-semibold text-slate-900 dark:text-slate-100">
            {token.slice(2, -2)}
          </strong>
        );
      } else if (token.startsWith('`') && token.endsWith('`')) {
        const codeText = token.slice(1, -1);
        parts.push(
          <code
            key={match.index}
            className="px-1.5 py-0.5 rounded text-[10.5px] font-mono bg-slate-200/80 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-indigo-700 dark:text-indigo-300 mx-0.5 font-medium shadow-2xs"
          >
            {codeText}
          </code>
        );
      }
      lastIndex = regex.lastIndex;
    }
    if (lastIndex < str.length) {
      parts.push(str.substring(lastIndex));
    }

    return parts;
  };

  return (
    <div className="space-y-2 text-xs leading-relaxed text-slate-800 dark:text-slate-200">
      {blocks.map((block, idx) => {
        if (block.type === 'h2') {
          return (
            <h2 key={idx} className="font-bold text-sm text-slate-900 dark:text-slate-100 mt-4 mb-1.5 flex items-center gap-1.5 border-b border-slate-200/80 dark:border-slate-700/80 pb-1">
              <Activity className="w-4 h-4 text-indigo-500" />
              <span>{renderInline(block.text)}</span>
            </h2>
          );
        }
        if (block.type === 'h3') {
          return (
            <h3 key={idx} className="font-bold text-xs uppercase tracking-wider text-indigo-900 dark:text-indigo-300 mt-3.5 mb-1.5 flex items-center gap-1.5 border-b border-slate-200/60 dark:border-slate-700/60 pb-1">
              <Layers className="w-3.5 h-3.5 text-indigo-500" />
              <span>{renderInline(block.text)}</span>
            </h3>
          );
        }
        if (block.type === 'h4') {
          return (
            <h4 key={idx} className="font-semibold text-xs text-slate-900 dark:text-slate-100 mt-2.5 mb-1 flex items-center gap-1.5">
              <AlertTriangle className="w-3 h-3 text-amber-500" />
              <span>{renderInline(block.text)}</span>
            </h4>
          );
        }
        if (block.type === 'divider') {
          return <hr key={idx} className="border-t border-slate-200/70 dark:border-slate-700/70 my-2.5" />;
        }
        if (block.type === 'table') {
          const [header, ...dataRows] = block.rows;
          return (
            <div key={idx} className="overflow-x-auto my-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900/60 shadow-2xs">
              <table className="w-full text-left border-collapse text-[11px]">
                {header && (
                  <thead>
                    <tr className="bg-slate-100/90 dark:bg-slate-800/90 border-b border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 font-semibold">
                      {header.map((h, i) => (
                        <th key={i} className="px-3 py-1.5 whitespace-nowrap">
                          {renderInline(h)}
                        </th>
                      ))}
                    </tr>
                  </thead>
                )}
                <tbody>
                  {dataRows.map((row, rIdx) => (
                    <tr
                      key={rIdx}
                      className="border-b border-slate-100 dark:border-slate-800/60 hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors"
                    >
                      {row.map((cell, cIdx) => (
                        <td key={cIdx} className="px-3 py-1.5 text-slate-700 dark:text-slate-300">
                          {renderInline(cell)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        }
        if (block.type === 'list') {
          return (
            <ul key={idx} className="my-1.5 space-y-1">
              {block.items.map((it, iIdx) => (
                <li key={iIdx} className="flex items-start gap-2 text-slate-700 dark:text-slate-300">
                  <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 mt-1.5 shrink-0" />
                  <span className="flex-1">{renderInline(it)}</span>
                </li>
              ))}
            </ul>
          );
        }
        return (
          <p key={idx} className="leading-relaxed my-1">
            {renderInline(block.text)}
          </p>
        );
      })}
    </div>
  );
}

export default function AICopilotDrawer({ isOpen, onClose }) {
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      role: 'assistant',
      content: "Hello! I am your ObserVault SRE Observability Copilot. I analyze your infrastructure health, active incidents, telemetry metrics, and traces using grounded AI. How can I assist you today?",
      cites: ["Cluster Telemetry", "Privacy Allowlist Active"]
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorNotice, setErrorNotice] = useState(null);

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const quickPrompts = [
    "What is the overall health of our infrastructure?",
    "Are there any active critical incidents?",
    "Which servers have high disk or memory usage?",
    "Summarize recent error traces and slow endpoints."
  ];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 150);
      scrollToBottom();
    }
  }, [isOpen, messages]);

  const handleSend = async (textToSend = null) => {
    const text = (textToSend || inputValue).trim();
    if (!text || loading) return;

    setErrorNotice(null);
    const userMsg = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: text
    };

    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setInputValue('');
    setLoading(true);

    try {
      // Build conversation history for context
      const history = newMessages
        .filter(m => m.id !== 'welcome')
        .map(m => ({ role: m.role, content: m.content }));

      const res = await api.sendCopilotChat(text, null, null, history);
      
      const assistantMsg = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: res.answer || "I've reviewed your observability data.",
        cites: res.cites_evidence || [],
        model: res.model_used
      };

      setMessages(prev => [...prev, assistantMsg]);
    } catch (err) {
      console.error("Copilot chat error:", err);
      const errMsg = err.message || "Failed to reach AI intelligence backend.";
      setErrorNotice(errMsg);
      setMessages(prev => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: 'assistant',
          isError: true,
          content: `AI Copilot Notice: ${errMsg}. If GROQ_API_KEY is not configured in your backend environment, please set it to enable live SRE intelligence.`
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleClearChat = () => {
    setMessages([
      {
        id: 'welcome',
        role: 'assistant',
        content: "Chat history cleared. Grounded telemetry context is refreshed. What would you like to investigate next?",
        cites: ["Cluster Telemetry"]
      }
    ]);
    setErrorNotice(null);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end animate-fadeIn">
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs transition-opacity" 
        onClick={onClose} 
      />

      {/* Drawer Container */}
      <div className="relative w-full max-w-xl md:max-w-2xl bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-800 shadow-2xl flex flex-col h-full z-10">
        
        {/* Header */}
        <div className="p-4 sm:p-5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-gradient-to-r from-indigo-50/50 via-white to-cyan-50/30 dark:from-slate-900 dark:via-slate-900 dark:to-indigo-950/20">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-gradient-to-tr from-cyan-500 to-indigo-600 text-white shadow-md shadow-indigo-500/20">
              <Brain className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-sm text-slate-900 dark:text-slate-100">
                  ObserVault SRE Copilot
                </h3>
                <span className="px-2 py-0.5 rounded-full text-[9px] font-mono font-bold bg-indigo-100 text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-700/50 flex items-center gap-1">
                  <Sparkles className="w-2.5 h-2.5" />
                  Groq 120B
                </span>
              </div>
              <p className="text-[11px] text-slate-500 dark:text-slate-400">
                Tenant-scoped, privacy-sanitized observability assistant
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1">
            <button
              onClick={handleClearChat}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
              title="Clear chat history"
            >
              <Trash2 className="w-4 h-4" />
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
              title="Close drawer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Messages Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 font-sans text-xs">
          {messages.map((m) => (
            <div
              key={m.id}
              className={`flex gap-3 ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {m.role === 'assistant' && (
                <div className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${
                  m.isError 
                    ? 'bg-rose-100 text-rose-600 dark:bg-rose-950 dark:text-rose-400' 
                    : 'bg-indigo-600 text-white'
                }`}>
                  {m.isError ? <AlertTriangle className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
                </div>
              )}

              <div className={`rounded-2xl p-4 space-y-2 transition-all ${
                m.role === 'user'
                  ? 'max-w-[80%] bg-indigo-600 text-white shadow-soft rounded-tr-xs'
                  : m.isError
                    ? 'w-full bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-900/40 text-rose-800 dark:text-rose-200 rounded-tl-xs'
                    : 'w-full bg-slate-50/90 dark:bg-slate-850 text-slate-800 dark:text-slate-100 border border-slate-200/90 dark:border-slate-750 shadow-2xs rounded-tl-xs'
              }`}>
                {m.role === 'user' ? (
                  <p className="whitespace-pre-wrap leading-relaxed font-sans text-xs">
                    {m.content}
                  </p>
                ) : (
                  <FormattedCopilotMessage content={m.content} />
                )}

                {/* Grounded Evidence Citations */}
                {m.cites && m.cites.length > 0 && (
                  <div className="pt-2.5 mt-2 border-t border-slate-200/50 dark:border-slate-700/50">
                    <div className="text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider flex items-center gap-1 mb-1.5">
                      <ShieldCheck className="w-3 h-3 text-indigo-500 shrink-0" />
                      <span>Verified Grounding</span>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {m.cites.map((cite, i) => (
                        <span
                          key={i}
                          className="px-2 py-0.5 rounded-md text-[10px] font-mono font-medium bg-white/80 dark:bg-slate-900/70 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 shadow-2xs"
                        >
                          {cite}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {m.role === 'user' && (
                <div className="w-7 h-7 rounded-lg bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-200 flex items-center justify-center shrink-0">
                  <User className="w-3.5 h-3.5" />
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className="flex gap-3 justify-start items-center text-slate-400">
              <div className="w-7 h-7 rounded-lg bg-indigo-600 text-white flex items-center justify-center shrink-0 animate-pulse">
                <Bot className="w-3.5 h-3.5" />
              </div>
              <div className="px-3.5 py-2.5 rounded-2xl bg-slate-100 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-indigo-500 animate-bounce" />
                <div className="w-2 h-2 rounded-full bg-indigo-500 animate-bounce [animation-delay:0.2s]" />
                <div className="w-2 h-2 rounded-full bg-indigo-500 animate-bounce [animation-delay:0.4s]" />
                <span className="text-[11px] font-mono text-slate-500 dark:text-slate-400 ml-1">
                  Synthesizing grounded response...
                </span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Quick Prompts Suggestions */}
        <div className="p-3 border-t border-slate-100 dark:border-slate-800/60 bg-slate-50/50 dark:bg-slate-900/30">
          <p className="text-[10px] uppercase font-bold text-slate-400 dark:text-slate-500 tracking-wider mb-1.5">
            Suggested Investigations
          </p>
          <div className="flex flex-wrap gap-1.5">
            {quickPrompts.map((qp, idx) => (
              <button
                key={idx}
                disabled={loading}
                onClick={() => handleSend(qp)}
                className="text-[11px] px-2.5 py-1 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:border-indigo-300 dark:hover:border-indigo-500 text-slate-600 dark:text-slate-300 transition text-left truncate max-w-full disabled:opacity-50"
              >
                {qp}
              </button>
            ))}
          </div>
        </div>

        {/* Input Bar */}
        <div className="p-3 sm:p-4 border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex items-center gap-2"
          >
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Ask Copilot about telemetry, servers, incidents..."
              disabled={loading}
              className="flex-1 text-xs px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-indigo-500 transition"
            />
            <button
              type="submit"
              disabled={loading || !inputValue.trim()}
              className="p-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 text-white shadow-md shadow-indigo-500/20 transition disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
              title="Send query"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
          <p className="text-[10px] text-slate-400 dark:text-slate-500 text-center mt-2">
            AI answers are grounded solely on your authorized cluster data. No credentials leave the edge.
          </p>
        </div>

      </div>
    </div>
  );
}
