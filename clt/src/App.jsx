import React, { useState, useRef, useEffect } from 'react';
import {
  Terminal, MessageSquare, ChevronDown, Plus,
  ArrowRight, GitBranch, GitPullRequest, RefreshCw,
  CircleDashed, Layers, Sun, Moon, Settings,
} from 'lucide-react';
import './App.css';

/* GitHub Copilot binoculars logo */
const CopilotLogo = () => (
  <svg width="56" height="56" viewBox="0 0 24 24" fill="currentColor" aria-label="GitHub Copilot">
    <path d="M9.5 2A4.5 4.5 0 0 0 5 6.5v1.586A3.5 3.5 0 0 0 2 11.5v1A3.5 3.5 0 0 0 5 15.95V17a4 4 0 0 0 4 4h1v-2H9a2 2 0 0 1-2-2v-.268A3.5 3.5 0 0 0 9.5 19h5a3.5 3.5 0 0 0 2.5-1.268V17a2 2 0 0 1-2 2h-1v2h1a4 4 0 0 0 4-4v-1.05A3.5 3.5 0 0 0 22 12.5v-1a3.5 3.5 0 0 0-3-3.464V6.5A4.5 4.5 0 0 0 14.5 2h-5Zm0 2h5A2.5 2.5 0 0 1 17 6.5V8H7V6.5A2.5 2.5 0 0 1 9.5 4ZM5 10h14a1.5 1.5 0 0 1 1.5 1.5v1A1.5 1.5 0 0 1 19 14H5a1.5 1.5 0 0 1-1.5-1.5v-1A1.5 1.5 0 0 1 5 10Zm2.5 1.5a1 1 0 1 0 0 2 1 1 0 0 0 0-2Zm9 0a1 1 0 1 0 0 2 1 1 0 0 0 0-2Z" />
  </svg>
);

export default function CopilotInterface() {
  const [input, setInput] = useState('');
  const [isDark, setIsDark] = useState(false);
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  // Settings modal
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settingsContent, setSettingsContent] = useState('');
  const [settingsSaving, setSettingsSaving] = useState(false);
  const [settingsStatus, setSettingsStatus] = useState(null);

  // Container status: { 'jira-svr': bool, 'post-svr': bool }
  const [containerStatus, setContainerStatus] = useState({});
  // Codespace lifecycle state
  const [codespaceState, setCodespaceState] = useState('idle');

  useEffect(() => {
    const poll = async () => {
      try {
        const res = await fetch('/api/containers/status');
        if (res.ok) setContainerStatus(await res.json());
      } catch { /* backend not up yet */ }
      try {
        const cs = await fetch('/api/codespace/status');
        if (cs.ok) {
          const data = await cs.json();
          setCodespaceState(data.state ?? 'idle');
        }
      } catch { /* backend not up yet */ }
    };
    poll();
    const id = setInterval(poll, 5000);
    return () => clearInterval(id);
  }, []);

  const openSettings = async () => {
    setSettingsStatus(null);
    setSettingsContent('');
    setSettingsOpen(true);          // open immediately so the user sees feedback
    try {
      const res = await fetch('/api/settings');
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      setSettingsContent(data.content ?? '');
    } catch (err) {
      setSettingsStatus('fetch-error');
      setSettingsContent(`# Could not load settings — is the Flask API running?\n# Error: ${err.message}`);
    }
  };

  const saveSettings = async () => {
    setSettingsSaving(true);
    setSettingsStatus(null);
    try {
      const res = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: settingsContent }),
      });
      const data = await res.json();
      setSettingsStatus(data.error ? 'error' : 'saved');
      if (!data.error) setTimeout(() => setSettingsOpen(false), 800);
    } catch {
      setSettingsStatus('error');
    } finally {
      setSettingsSaving(false);
    }
  };

  // Scroll to bottom whenever messages update
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || isLoading) return;

    const userMsg = { role: 'user', content: text };
    const nextMessages = [...messages, userMsg];
    setMessages(nextMessages);
    setInput('');
    setIsLoading(true);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, history: messages }),
      });
      const data = await res.json();
      setMessages([...nextMessages, {
        role: 'assistant',
        content: data.error ? `Error: ${data.error}` : data.response,
      }]);
    } catch (err) {
      setMessages([...nextMessages, {
        role: 'assistant',
        content: `Connection error: ${err.message}`,
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    // Ctrl+Enter or Cmd+Enter to send
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className={`copilot-page${isDark ? ' dark' : ''}`}>
      {/* Top bar */}
      <header className="topbar">
        {/* Container status indicators */}
        <div className="container-indicators">
          {/* Codespace badge — only shown when CODESPACE_REPO is set */}
          {codespaceState !== 'idle' && (
            <span
              className={`container-indicator ${
                codespaceState === 'ready'    ? 'indicator--up' :
                codespaceState.startsWith('error') ? 'indicator--down' :
                'indicator--unknown'
              }`}
              title={`Codespace: ${codespaceState}`}
            >
              <span className="indicator-dot" />
              {codespaceState === 'ready'    ? 'Codespace' :
               codespaceState === 'creating' ? 'Starting…' :
               'CS Error'}
            </span>
          )}
          {[
            { key: 'jira-svr', label: 'Jira' },
            { key: 'post-svr', label: 'Post' },
          ].map(({ key, label }) => {
            const running = containerStatus[key];
            const statusClass = running === true
              ? 'indicator--up'
              : running === false
                ? 'indicator--down'
                : 'indicator--unknown';
            return (
              <span key={key} className={`container-indicator ${statusClass}`} title={`${key}: ${running === true ? 'running' : running === false ? 'stopped' : 'unknown'}`}>
                <span className="indicator-dot" />
                {label}
              </span>
            );
          })}
        </div>

        <button className="theme-toggle" onClick={openSettings} title="Settings">
          <Settings size={14} />
        </button>
        <button className="theme-toggle" onClick={() => setIsDark(d => !d)} title={isDark ? 'Switch to light' : 'Switch to dark'}>
          {isDark ? <Sun size={14} /> : <Moon size={14} />}
        </button>
        <button className="cli-btn">
          <Terminal size={13} />
          CLI
        </button>
      </header>

      {/* Main content */}
      <main className="main-content">

        {/* Logo — hide once conversation starts */}
        {messages.length === 0 && (
          <div className="copilot-logo">
            <CopilotLogo />
          </div>
        )}

        {/* Ask box */}
        <div className="ask-container">
          <textarea
            className="ask-input"
            placeholder="Ask anything"
            rows={2}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <div className="ask-toolbar">
            <div className="toolbar-left">
              <button className="toolbar-btn">
                <MessageSquare size={13} />
                Ask
                <ChevronDown size={11} />
              </button>
              <button className="toolbar-btn">
                <Layers size={13} />
                All repositories
                <ChevronDown size={11} />
              </button>
              <button className="toolbar-btn-icon">
                <Plus size={13} />
              </button>
            </div>
            <div className="toolbar-right">
              <span className="model-label">
                GPT-5.2
                <ChevronDown size={11} />
              </span>
              <button
                className={`send-btn${isLoading ? ' send-btn--loading' : ''}`}
                onClick={sendMessage}
                disabled={isLoading || !input.trim()}
                title="Send (Ctrl+Enter)"
              >
                {isLoading
                  ? <RefreshCw size={14} className="spin" />
                  : <ArrowRight size={14} />}
              </button>
            </div>
          </div>
        </div>

        {/* Quick-action pills */}
        <div className="quick-actions">
          <button className="action-btn"><RefreshCw size={13} />Agent</button>
          <button className="action-btn"><CircleDashed size={13} />Create issue</button>
          <button className="action-btn"><GitBranch size={13} />Git<ChevronDown size={11} /></button>
          <button className="action-btn"><GitPullRequest size={13} />Pull requests<ChevronDown size={11} /></button>
        </div>

        {/* Messages / Recent sessions */}
        <div className="sessions-section">
          <p className="sessions-title">Recent agent sessions</p>

          {messages.length === 0 ? (
            <div className="sessions-empty">
              No sessions found. Create one by sending a prompt above.
            </div>
          ) : (
            <div className="messages-list">
              {messages.map((msg, i) => (
                <div key={i} className={`message message--${msg.role}`}>
                  <span className="message-label">
                    {msg.role === 'user' ? 'You' : 'das_buddy'}
                  </span>
                  <p className="message-content">{msg.content}</p>
                </div>
              ))}
              {isLoading && (
                <div className="message message--assistant">
                  <span className="message-label">das_buddy</span>
                  <p className="message-content message-content--thinking">Thinking…</p>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

      </main>

      {/* Settings modal */}
      {settingsOpen && (
        <div className="modal-overlay" onClick={() => setSettingsOpen(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <span className="modal-title"><Settings size={14} /> Settings</span>
              <button className="modal-close" onClick={() => setSettingsOpen(false)}>✕</button>
            </div>
            <p className="modal-desc">
              Edit environment variables for <code>svr/.settings</code>. One <code>KEY=value</code> per line.
            </p>
            <textarea
              className="modal-editor"
              value={settingsContent}
              onChange={(e) => setSettingsContent(e.target.value)}
              spellCheck={false}
            />
            {settingsStatus === 'saved' && (
              <p className="modal-status modal-status--ok">✓ Saved successfully</p>
            )}
            {settingsStatus === 'error' && (
              <p className="modal-status modal-status--err">✗ Failed to save</p>
            )}
            {settingsStatus === 'fetch-error' && (
              <p className="modal-status modal-status--err">⚠ Could not reach the API — start the Flask server (<code>python svr/api.py</code>)</p>
            )}
            <div className="modal-footer">
              <button className="modal-btn modal-btn--cancel" onClick={() => setSettingsOpen(false)}>
                Cancel
              </button>
              <button className="modal-btn modal-btn--save" onClick={saveSettings} disabled={settingsSaving}>
                {settingsSaving ? 'Saving…' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
