import React, { useState } from 'react';
import {
  Terminal, MessageSquare, ChevronDown, Plus,
  ArrowRight, GitBranch, GitPullRequest, RefreshCw,
  CircleDashed, Layers,
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

  return (
    <div className="copilot-page">
      {/* Top bar */}
      <header className="topbar">
        <button className="cli-btn">
          <Terminal size={13} />
          CLI
        </button>
      </header>

      {/* Main content */}
      <main className="main-content">

        {/* Logo */}
        <div className="copilot-logo">
          <CopilotLogo />
        </div>

        {/* Ask box */}
        <div className="ask-container">
          <textarea
            className="ask-input"
            placeholder="Ask anything"
            rows={2}
            value={input}
            onChange={(e) => setInput(e.target.value)}
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
              <button className="send-btn">
                <ArrowRight size={14} />
              </button>
            </div>
          </div>
        </div>

        {/* Quick-action pills */}
        <div className="quick-actions">
          <button className="action-btn">
            <RefreshCw size={13} />
            Agent
          </button>
          <button className="action-btn">
            <CircleDashed size={13} />
            Create issue
          </button>
          <button className="action-btn">
            <GitBranch size={13} />
            Git
            <ChevronDown size={11} />
          </button>
          <button className="action-btn">
            <GitPullRequest size={13} />
            Pull requests
            <ChevronDown size={11} />
          </button>
        </div>

        {/* Recent sessions */}
        <div className="sessions-section">
          <p className="sessions-title">Recent agent sessions</p>
          <div className="sessions-empty">
            No sessions found. Create one by sending a prompt above.
          </div>
        </div>

      </main>
    </div>
  );
}
