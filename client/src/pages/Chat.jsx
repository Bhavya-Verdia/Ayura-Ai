import React, { useState, useEffect, useRef } from 'react';
import client from '../api/client';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Bot, Send, Sparkles, AlertTriangle, Loader2, Zap } from 'lucide-react';
import './Dashboard.css';
import './Chat.css';

const SUGGESTIONS = [
  'What should a Vata dosha eat today?',
  'Give me a morning yoga routine',
  'I have joint pain — what remedies help?',
  'Explain my panchakarma detox plan',
];

function TypingDots() {
  return (
    <div className="chat-typing-dots">
      <span /><span /><span />
    </div>
  );
}

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

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

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = (content) => {
    if (!content.trim() || isLoading) return;
    const userMessage = { role: 'user', content };
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    const activeSession = sessionId || crypto.randomUUID();
    if (!sessionId) setSessionId(activeSession);

    let wsBase = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
    wsBase = wsBase.replace('http', 'ws');
    // Auth is via the ayura_access HTTP-only cookie sent automatically by the browser.
    // Do NOT append a token query param — that exposes JWTs in server logs.
    const wsUrl = `${wsBase}/chat/ws/${activeSession}`;

    const ws = new WebSocket(wsUrl);
    let currentMessage = '';

    setMessages(prev => [...prev, { role: 'ai', content: '', sources: [], status: 'Thinking…', typing: true }]);

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

      <div className="chat-canvas">
        <div className="chat-history">
          {messages.length === 0 && (
            <div className="chat-empty-state">
              <div className="chat-empty-icon-wrap">
                <Sparkles size={40} strokeWidth={1.5} />
              </div>
              <h3 className="chat-empty-title">Ask Ayura anything</h3>
              <p className="chat-empty-sub">Your personal AI wellness advisor, powered by Ayurvedic wisdom.</p>
              <div className="chat-suggestions">
                {SUGGESTIONS.map(s => (
                  <button
                    key={s}
                    className="chat-suggestion-chip"
                    onClick={() => handleSend(s)}
                  >
                    {s}
                  </button>
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
                </div>
              </div>
            );
          })}

          <div ref={messagesEndRef} />
        </div>

        <form className="chat-input-area" onSubmit={handleSubmit}>
          <div className="chat-input-wrapper">
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="How are you feeling today?"
              disabled={isLoading}
            />
            <button type="submit" className="chat-send-btn" disabled={isLoading || !inputValue.trim()}>
              <Send size={18} strokeWidth={2.5} />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
