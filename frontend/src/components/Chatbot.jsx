import React, { useState, useEffect, useRef } from 'react';
import { fetchWithAuth } from '../utils/api';

export default function Chatbot() {
  const [active, setActive] = useState(false);
  const [messages, setMessages] = useState([
    {
      sender: 'agent',
      text: 'Bonjour ! Je suis l\'assistant intelligent d\'Orbus Sentinel (expérimental) 🤖.',
      html: 'Bonjour ! Je suis l\'assistant intelligent d\'Orbus Sentinel (expérimental) 🤖.<br><br>Je peux vous aider à analyser la base de données douanière locale, vérifier les indicateurs de risques ou exporter des rapports en CSV. Que souhaitez-vous savoir ?'
    }
  ]);
  const [inputVal, setInputVal] = useState('');
  const [typing, setTyping] = useState(false);

  const historyRef = useRef(null);

  useEffect(() => {
    if (historyRef.current) {
      historyRef.current.scrollTop = historyRef.current.scrollHeight;
    }
  }, [messages, typing]);

  const escapeHTML = (str) => {
    return str.replace(/[&<>'"]/g, 
      tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
    );
  };

  const formatMarkdown = (text) => {
    let html = escapeHTML(text);
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\n/g, '<br>');
    return html;
  };

  const handleSend = async (messageText) => {
    const message = messageText || inputVal.trim();
    if (!message) return;

    if (!messageText) {
      setInputVal('');
    }

    // Add user message
    setMessages(prev => [...prev, { sender: 'user', text: message, html: escapeHTML(message) }]);
    setTyping(true);

    try {
      const response = await fetchWithAuth('/api/assistant/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: message })
      });

      setTyping(false);

      if (response.ok) {
        const data = await response.json();
        setMessages(prev => [...prev, { 
          sender: 'agent', 
          text: data.reply, 
          html: formatMarkdown(data.reply),
          exportUrl: data.export_url 
        }]);
      } else {
        const errData = await response.json().catch(() => ({}));
        const errMsg = errData.detail || 'Erreur lors de la communication avec l\'assistant.';
        setMessages(prev => [...prev, { 
          sender: 'agent', 
          text: errMsg, 
          html: `<span style="color: var(--danger);">⚠️ ${escapeHTML(errMsg)}</span>` 
        }]);
      }
    } catch (err) {
      setTyping(false);
      setMessages(prev => [...prev, { 
        sender: 'agent', 
        text: 'Impossible de contacter le serveur.', 
        html: '<span style="color: var(--danger);">⚠️ Impossible de contacter le serveur.</span>' 
      }]);
    }
  };

  const handleSuggestion = (text) => {
    handleSend(text);
  };

  return (
    <>
      {/* Bubble */}
      <div className="chatbot-bubble" onClick={() => setActive(!active)}>
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
      </div>

      {/* Window */}
      <div className={`chatbot-window ${active ? 'active' : ''}`}>
        <div className="chatbot-header">
          <div className="chatbot-title">
            <span className="chatbot-status"></span>
            <span>Assistant Orbus Sentinel (expérimental)</span>
          </div>
          <button className="chatbot-close" onClick={() => setActive(false)}>&times;</button>
        </div>
        
        <div className="chatbot-history" ref={historyRef}>
          {messages.map((msg, idx) => (
            <div key={idx} className={`chat-msg ${msg.sender}`}>
              <div dangerouslySetInnerHTML={{ __html: msg.html }} />
              {msg.exportUrl && (
                <a href={msg.exportUrl} className="chat-msg-btn" target="_blank" rel="noreferrer">
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" style={{ width: '14px', height: '14px', display: 'inline-block', verticalAlign: 'middle', marginRight: '4px' }}>
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg> 
                  Télécharger l'Export
                </a>
              )}
            </div>
          ))}
          {typing && (
            <div className="chatbot-typing">
              <span></span>
              <span></span>
              <span></span>
            </div>
          )}
        </div>

        <div className="chatbot-suggestions">
          <span className="chat-sug-pill" onClick={() => handleSuggestion('Combien de dossiers au total ?')}>Combien de dossiers ?</span>
          <span className="chat-sug-pill" onClick={() => handleSuggestion('Quels sont les principaux pays d\'origine ?')}>Pays d'origine</span>
          <span className="chat-sug-pill" onClick={() => handleSuggestion("Montre-moi les anomalies récentes")}>Anomalies</span>
          <span className="chat-sug-pill" onClick={() => handleSuggestion('Exporter les dossiers en CSV')}>Export CSV</span>
        </div>

        <div className="chatbot-input-bar">
          <input 
            type="text" 
            placeholder="Posez votre question..." 
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') handleSend(); }}
          />
          <button className="chatbot-send-btn" onClick={() => handleSend()}>
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
            </svg>
          </button>
        </div>
      </div>
    </>
  );
}
