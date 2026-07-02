import React, { useState, useEffect, useRef } from 'react';
import client from '../api/client';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { m, AnimatePresence } from 'framer-motion';
import { Bot, Send, Sparkles, AlertTriangle, Loader2, Zap, Copy, Check, ChevronDown, Leaf, Soup, ClipboardList, Lightbulb, AlarmClock } from 'lucide-react';
import './Dashboard.css';
import './Chat.css';

const SUGGESTION_GROUPS = [
  {
    category: 'Wellness', Icon: Leaf,
    prompts: ['What should a Vata dosha eat today?', 'Give me a morning Ayurvedic routine'],
  },
  {
    category: 'Remedies', Icon: Soup,
    prompts: ['I have joint pain — what helps?', 'Natural remedy for better sleep'],
  },
  {
    category: 'Plans', Icon: ClipboardList,
    prompts: ['Explain my panchakarma detox plan', 'How do I adapt my gym plan?'],
  },
  {
    category: 'Insight', Icon: Lightbulb,
    prompts: ['What is my dominant dosha?', 'How do seasons affect Vata?'],
  },
]

function formatMsgTime(ts) {
  if (!ts) return ''
  return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function TypingDots() {
  return (
    <div className="chat-typing-dots">
      <span /><span /><span />
    </div>
  );
}

export default function Chat() {
  const [messages, setMessages]       = useState([]);
  const [inputValue, setInputValue]   = useState('');
  const [isLoading, setIsLoading]     = useState(false);
  const [sessionId, setSessionId]     = useState(null);
  const [copiedIdx, setCopiedIdx]     = useState(null);
  const [showScrollFab, setShowScrollFab] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef       = useRef(null);
  const historyRef     = useRef(null);
  const wsRef          = useRef(null);

  // Close any in-flight WebSocket when the component unmounts
  useEffect(() => {
    return () => {
      if (wsRef.current && wsRef.current.readyState < WebSocket.CLOSING) {
        wsRef.current.close()
      }
    }
  }, [])

  useEffect(() => {
    const fetchSession = async () => {
      try {
        const { data: sessions } = await client.get('/chat/sessions');
        if (sessions.length > 0) {
          const sid = sessions[0].session_id;
          setSessionId(sid);
          const { data: history } = await client.get(`/chat/sessions/${sid}`);
          setMessages(history);
        }
      } catch (error) {
        console.error('Failed to load chat history', error);
      }
    };
    fetchSession();
  }, []);

  // Auto-scroll to bottom unless user has scrolled up
  useEffect(() => {
    if (!showScrollFab) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, showScrollFab]);

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
      inputRef.current.style.height = Math.min(inputRef.current.scrollHeight, 180) + 'px';
    }
  }, [inputValue]);

  // Scroll FAB visibility
  useEffect(() => {
    const el = historyRef.current;
    if (!el) return;
    const onScroll = () => {
      const dist = el.scrollHeight - el.scrollTop - el.clientHeight;
      setShowScrollFab(dist > 120);
    };
    el.addEventListener('scroll', onScroll, { passive: true });
    return () => el.removeEventListener('scroll', onScroll);
  }, []);

  const handleSend = (content) => {
    if (!content.trim() || isLoading) return;
    // eslint-disable-next-line react-hooks/purity
    const userMessage = { role: 'user', content, timestamp: Date.now() };
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    const activeSession = sessionId || crypto.randomUUID();
    if (!sessionId) setSessionId(activeSession);

    const apiBase = import.meta.env.VITE_API_URL || '/api';
    let wsUrl;
    if (apiBase.startsWith('http')) {
      wsUrl = `${apiBase.replace(/^http/, 'ws')}/chat/ws/${activeSession}`;
    } else {
      // Relative base path — derive ws(s):// from current page origin
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      wsUrl = `${wsProtocol}//${window.location.host}${apiBase}/chat/ws/${activeSession}`;
    }

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;
    let currentMessage = '';

    setMessages(prev => [...prev, { role: 'ai', content: '', sources: [], status: 'Thinking…', typing: true, timestamp: Date.now() }]);

    ws.onopen = () => { ws.send(content); };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'status') {
          setMessages(prev => {
            const arr = [...prev];
            arr[arr.length - 1] = { ...arr[arr.length - 1], status: data.message };
            return arr;
          });
        } else if (data.type === 'chunk') {
          currentMessage += data.content;
          setMessages(prev => {
            const arr = [...prev];
            arr[arr.length - 1] = { ...arr[arr.length - 1], content: currentMessage, status: null, typing: false };
            return arr;
          });
        } else if (data.type === 'actions') {
          setMessages(prev => {
            const arr = [...prev];
            arr[arr.length - 1] = {
              ...arr[arr.length - 1],
              actions: {
                reminders: data.reminders_set || [],
                plansAdapting: data.plans_adapting || [],
              },
            };
            return arr;
          });
        } else if (data.type === 'done') {
          setMessages(prev => {
            const arr = [...prev];
            arr[arr.length - 1] = { ...arr[arr.length - 1], sources: data.sources || [], typing: false };
            return arr;
          });
          setIsLoading(false);
          ws.close();
        }
      } catch (err) {
        console.error('WS parse error', err);
      }
    };

    ws.onerror = (err) => {
      console.error('WebSocket error:', err);
      setMessages(prev => {
        const arr = [...prev];
        if (arr[arr.length - 1].status === 'Thinking…') {
          arr[arr.length - 1] = { ...arr[arr.length - 1], content: 'Sorry, I am having trouble connecting to the server.', status: null, typing: false };
        }
        return arr;
      });
      setIsLoading(false);
    };

    ws.onclose = () => {
      setMessages(prev => {
        const arr = [...prev];
        if (arr[arr.length - 1].status === 'Thinking…') {
          arr[arr.length - 1] = { ...arr[arr.length - 1], content: 'Connection closed unexpectedly. Please try again.', status: null, typing: false };
        }
        return arr;
      });
      setIsLoading(false);
    };
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    handleSend(inputValue);
  };

  const hasEmergency = (content) => content?.toLowerCase().includes('urgency: emergency') || content?.toLowerCase().includes('consult a doctor');
  const hasAdapted   = (content) => content?.toLowerCase().includes('plan_adapted: true') || content?.toLowerCase().includes('plan updated');

  function copyMessage(content, idx) {
    navigator.clipboard.writeText(content).catch(() => {});
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 1600);
  }

  return (
    <div className="chat-page-root">
      <header className="chat-header">
        <div className="chat-header-icon">
          <Zap size={24} strokeWidth={2.5} />
        </div>
        <div>
          <h1 className="chat-header-title">Health AI Assistant</h1>
          <p className="chat-header-subtitle">Ask questions, report symptoms, or request personalised plan adaptations.</p>
        </div>
      </header>

      <div className="chat-canvas" style={{ position: 'relative' }}>
        <div className="chat-history" ref={historyRef}>
          {messages.length === 0 && (
            <div className="chat-empty-state">
              <div className="chat-empty-icon-wrap">
                <Sparkles size={40} strokeWidth={1.5} />
              </div>
              <h3 className="chat-empty-title">Ask Ayura anything</h3>
              <p className="chat-empty-sub">Your personal AI wellness advisor — ask about your plans, symptoms, dosha, or daily routine.</p>
              <div className="chat-suggestion-groups">
                {SUGGESTION_GROUPS.map(group => (
                  <div key={group.category} className="chat-suggestion-group">
                    <div className="chat-suggestion-group-header">
                      <span style={{ display: 'inline-flex', color: 'var(--ayura-teal)' }}><group.Icon size={15} strokeWidth={2} /></span>
                      {group.category}
                    </div>
                    {group.prompts.map(p => (
                      <button key={p} onClick={() => handleSend(p)}>{p}</button>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, idx) => {
            const isEmergency = msg.role === 'ai' && hasEmergency(msg.content);
            const isAdapted   = msg.role === 'ai' && hasAdapted(msg.content);
            const isUser      = msg.role === 'user';

            return (
              <div key={idx} className={`chat-bubble-row ${isUser ? 'user' : 'ai'}`}>
                {!isUser && (
                  <div className="chat-ai-avatar">
                    <Zap size={14} strokeWidth={2.5} />
                  </div>
                )}
                <div className="chat-bubble-wrapper">
                  {isEmergency && (
                    <div className="chat-bubble-alert">
                      <AlertTriangle size={14} strokeWidth={2.5} />
                      Please consult a doctor immediately.
                    </div>
                  )}
                  {isAdapted && (
                    <div className="chat-bubble-success">
                      <Sparkles size={14} strokeWidth={2.5} />
                      Your daily plan has been updated!
                    </div>
                  )}

                  <div className={`chat-bubble ${isUser ? 'user' : 'ai'}`}>
                    {msg.typing && !msg.content ? (
                      <TypingDots />
                    ) : isUser ? (
                      msg.content
                    ) : (
                      <div className="chat-markdown">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {msg.content || ''}
                        </ReactMarkdown>
                      </div>
                    )}
                  </div>

                  {!isUser && msg.status && !msg.content && (
                    <div className="ai-status-indicator">
                      <Loader2 size={14} strokeWidth={2} />
                      {msg.status}
                    </div>
                  )}
                  {!isUser && !msg.typing && msg.content && (
                    <button
                      className="chat-copy-btn"
                      onClick={() => copyMessage(msg.content, idx)}
                      title="Copy message"
                      aria-label="Copy message"
                    >
                      {copiedIdx === idx
                        ? <Check size={12} strokeWidth={2.5} />
                        : <Copy size={12} strokeWidth={2} />}
                    </button>
                  )}
                  {!isUser && msg.actions && (msg.actions.reminders?.length > 0 || msg.actions.plansAdapting?.length > 0) && (
                    <div className="chat-action-chips" style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 8 }}>
                      {msg.actions.reminders?.map((r, i) => (
                        <span key={`rem-${i}`} style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: '0.72rem', fontWeight: 600, padding: '3px 9px', borderRadius: 999, background: 'rgba(74,222,128,0.12)', color: '#5cab74', border: '1px solid rgba(74,222,128,0.3)' }}>
                          <AlarmClock size={12} strokeWidth={2} /> Reminder set — {r.title} at {r.time}
                        </span>
                      ))}
                      {msg.actions.plansAdapting?.map((p, i) => (
                        <span key={`pln-${i}`} style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: '0.72rem', fontWeight: 600, padding: '3px 9px', borderRadius: 999, background: 'rgba(230,162,60,0.12)', color: '#e6a23c', border: '1px solid rgba(230,162,60,0.3)' }}>
                          <Sparkles size={12} strokeWidth={2} /> Regenerating your {p} plan…
                        </span>
                      ))}
                    </div>
                  )}
                  {!msg.typing && msg.timestamp && (
                    <span className="chat-bubble-time">{formatMsgTime(msg.timestamp)}</span>
                  )}
                </div>
              </div>
            );
          })}

          <div ref={messagesEndRef} />
        </div>

        {/* Scroll-to-bottom FAB */}
        <AnimatePresence>
          {showScrollFab && (
            <m.button
              className="chat-scroll-fab"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              transition={{ duration: 0.2 }}
              onClick={() => {
                setShowScrollFab(false);
                messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
              }}
              aria-label="Scroll to bottom"
            >
              <ChevronDown size={18} strokeWidth={2.5} />
            </m.button>
          )}
        </AnimatePresence>

        <form className="chat-input-area" onSubmit={handleSubmit}>
          <div className="chat-input-wrapper">
            <textarea
              ref={inputRef}
              className="chat-text-input"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(e); }
              }}
              placeholder="How are you feeling today? (Shift+Enter for new line)"
              disabled={isLoading}
              rows={1}
            />
            <button type="submit" className="chat-send-btn" disabled={isLoading || !inputValue.trim()} aria-label="Send message">
              <Send size={18} strokeWidth={2.5} />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
