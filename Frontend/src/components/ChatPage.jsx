import React, { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Bot, User, Sparkles } from "lucide-react";
import MessageBubble from "./MessageBubble.jsx";

const initialMessages = [
  {
    id: 1,
    role: "assistant",
    content: "Hey Priyanshu 👋 I'm your chatbot. Ask me anything!",
    time: "11:00 AM",
  },
];

export default function ChatPage() {
  const [messages, setMessages] = useState(initialMessages);
  const [input, setInput] = useState("");
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMsg = {
      id: Date.now(),
      role: "user",
      content: input.trim(),
      time: new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");

    // TODO: here you can call your backend:
    // const res = await fetch("http://localhost:8000/chat", { ... })
    // const data = await res.json();

    // temporary fake reply
    setTimeout(() => {
      const botMsg = {
        id: Date.now() + 1,
        role: "assistant",
        content: "This is a mock reply 🤖 — plug your Azure/MCP endpoint here.",
        time: new Date().toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        }),
      };
      setMessages((prev) => [...prev, botMsg]);
    }, 500);
  };

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="chat-wrapper">
      {/* Header */}
      <header className="chat-header">
        <div className="chat-header-left">
          <div className="avatar-bot">
            <Bot size={20} />
          </div>
          <div>
            <div className="chat-title">AG UI • Chat Assistant</div>
            <div className="chat-subtitle">
              <Sparkles size={13} /> online • streaming mock
            </div>
          </div>
        </div>
        <div className="chat-header-right">
          <button className="header-pill">New Chat</button>
        </div>
      </header>

      {/* Messages */}
      <main className="chat-main">
        <AnimatePresence>
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 6, scale: 0.995 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.12 }}
            >
              <MessageBubble role={msg.role} content={msg.content} time={msg.time} />
            </motion.div>
          ))}
        </AnimatePresence>
        <div ref={bottomRef} />
      </main>

      {/* Input */}
      <footer className="chat-footer">
        <div className="input-box">
          <textarea
            rows="1"
            className="input-text"
            placeholder="Type your message…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKey}
          />
          <button onClick={sendMessage} className="send-btn" aria-label="Send message">
            <Send size={18} />
          </button>
        </div>
      </footer>
    </div>
  );
}
