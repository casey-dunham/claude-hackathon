import { useState, useRef, useEffect } from 'react';
import { ChatContextInput, ChatMessage } from '../services/types';
import { sendChatMessage } from '../services/api';

interface Props {
  messages: ChatMessage[];
  onNewMessage: (userMsg: ChatMessage, assistantMsg: ChatMessage) => void;
  backendOnline: boolean;
  userLat?: number;
  userLng?: number;
}

export default function ChatPanel({ messages, onNewMessage, backendOnline, userLat, userLng }: Props) {
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  async function handleSend() {
    const text = input.trim();
    if (!text || loading) return;

    setInput('');
    setLoading(true);

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text,
      created_at: new Date().toISOString(),
    };

    try {
      if (backendOnline) {
        const res = await sendChatMessage(text, userLat, userLng);
        const assistantMsg: ChatMessage = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: res.reply,
          created_at: new Date().toISOString(),
        };
        onNewMessage(userMsg, assistantMsg);
      } else {
        const assistantMsg: ChatMessage = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: 'Backend is offline. Start the FastAPI server to enable the AI coach.',
          created_at: new Date().toISOString(),
        };
        onNewMessage(userMsg, assistantMsg);
      }
    } catch {
      const errorMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: 'Something went wrong. Please try again.',
        created_at: new Date().toISOString(),
      };
      onNewMessage(userMsg, errorMsg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="bg-white border border-[#f0f0f0] rounded-xl flex flex-col" style={{ height: '400px' }}>
      {/* Header */}
      <div className="flex items-center gap-2 px-5 py-3.5 border-b border-[#f0f0f0]">
        <div
          className={`w-1.5 h-1.5 rounded-full ${backendOnline ? 'bg-green-500' : 'bg-[#d4d4d8]'}`}
        />
        <span className="text-sm font-medium text-[#18181b]">Food Coach</span>
        {!backendOnline && (
          <span className="text-[10px] text-[#a1a1aa] ml-auto">offline</span>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <p className="text-xs text-[#a1a1aa] text-center leading-relaxed">
              Ask me about healthy food options nearby,<br />
              nutrition info, or say "delete last" to remove a log item.
            </p>
          </div>
        )}
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-lg px-3.5 py-2.5 text-[13px] leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-[#18181b] text-white'
                  : 'bg-[#f4f4f5] text-[#3f3f46]'
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-[#f4f4f5] rounded-lg px-3.5 py-2.5 text-[13px] text-[#a1a1aa]">
              Thinking...
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-4 py-3 border-t border-[#f0f0f0]">
        <div className="flex gap-2">
          <input
            className="flex-1 px-3.5 py-2.5 text-[13px] border border-[#e4e4e7] rounded-lg bg-[#fafafa] outline-none focus:border-[#a1a1aa] focus:bg-white transition-colors placeholder:text-[#c4c4cc]"
            placeholder="Ask about food nearby..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            disabled={loading}
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="w-10 h-10 flex items-center justify-center bg-[#18181b] rounded-lg disabled:opacity-40 transition-opacity"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
              <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
