import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Send } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import api from '../api';
import './Chat.css';

const Chat = () => {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const messagesEndRef = useRef(null);
  
  // Create a ref to store current messages during stream
  const messagesRef = useRef(messages);
  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  useEffect(() => {
    if (sessionId) {
      loadHistory();
    } else {
      setMessages([]);
    }
  }, [sessionId]);

  const loadHistory = async () => {
    try {
      const res = await api.get(`/chat/sessions/${sessionId}`);
      setMessages(res.data.messages || []);
    } catch (err) {
      console.error('Failed to load session');
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;

    const userMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsStreaming(true);

    // Placeholder for assistant message
    const tempAssistantMsgId = Date.now().toString();
    setMessages(prev => [...prev, { id: tempAssistantMsgId, role: 'assistant', content: '' }]);

    try {
      const token = localStorage.getItem('token');
      
      const res = await fetch('http://localhost:8000/api/v1/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          message: userMessage.content,
          stream: true,
          session_id: sessionId || null
        })
      });

      const reader = res.body.getReader();
      const decoder = new TextDecoder('utf-8');
      
      let fullResponse = '';
      let newSessionId = sessionId;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.replace('data: ', '').trim();
            if (dataStr) {
              try {
                const data = JSON.parse(dataStr);
                
                if (!newSessionId && data.session_id) {
                  newSessionId = data.session_id;
                }

                if (data.type === 'token' || data.type === 'status') {
                  fullResponse += (data.content || '');
                  
                  // Update the last message
                  setMessages(prev => {
                    const newMsgs = [...prev];
                    newMsgs[newMsgs.length - 1].content = fullResponse;
                    return newMsgs;
                  });
                }
              } catch (e) {
                console.error("Parse error", e);
              }
            }
          }
        }
      }

      setIsStreaming(false);

      if (!sessionId && newSessionId) {
        navigate(`/chat/${newSessionId}`);
      }
      
    } catch (err) {
      console.error(err);
      setIsStreaming(false);
    }
  };

  return (
    <div className="chat-container">
      <div className="messages-area">
        {messages.length === 0 && (
          <div style={{ textAlign: 'center', marginTop: 'auto', marginBottom: 'auto', color: 'var(--text-color)' }}>
            <h2>How can I help you today?</h2>
            <p>Start a new conversation by typing a message below.</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={msg.id || i} className={`message ${msg.role}`}>
            <div className="message-content">
              <ReactMarkdown>{msg.content}</ReactMarkdown>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSend} className="input-area">
        <input
          type="text"
          className="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your message here..."
          disabled={isStreaming}
        />
        <button type="submit" className="send-button" disabled={!input.trim() || isStreaming}>
          <Send size={18} />
        </button>
      </form>
    </div>
  );
};

export default Chat;
