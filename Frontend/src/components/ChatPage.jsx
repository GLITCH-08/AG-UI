import React, { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Bot, Sparkles } from "lucide-react";
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
  const [isLoading, setIsLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

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
    const userPrompt = input.trim();
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch(
        `http://127.0.0.1:8001/get_data?userprompt=${encodeURIComponent(userPrompt)}`,
        {
          method: "POST",
          headers: {
            Accept: "text/event-stream",
          },
        }
      );

      if (!response.ok || !response.body) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      // Create a blank assistant message slot
      let assistantMsg = {
        id: Date.now() + 1,
        role: "assistant",
        content: "",
        time: new Date().toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        }),
      };
      setMessages((prev) => [...prev, assistantMsg]);

      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const parts = buffer.split("\n");
        buffer = parts.pop() || ""; // keep incomplete line in buffer

        for (const part of parts) {
          if (part.startsWith("data: ")) {
            const data = part.slice(6);
            try {
              const event = JSON.parse(data);

              if (event.type === "TEXT_MESSAGE_CONTENT") {
                // append streamed text live
                assistantMsg.content += event.delta;
                setMessages((prev) => {
                  const updated = [...prev];
                  updated[updated.length - 1] = { ...assistantMsg };
                  return updated;
                });
              } else if (event.type === "TOOL_CALL_START") {
                console.log("🧩 Tool call started:", event.toolCallName);
              } else if (event.type === "RUN_FINISHED" || event.type === "TEXT_MESSAGE_END") {
                console.log("✅ Stream finished");
                setIsLoading(false);
              }
            } catch (err) {
              console.error("Failed to parse event:", err);
            }
          }
        }
      }
    } catch (error) {
      console.error("Error:", error);
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 2,
          role: "assistant",
          content: "Sorry, an error occurred. Please try again.",
          time: new Date().toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          }),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
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
              <Sparkles size={13} /> {isLoading ? "typing..." : "online"}
            </div>
          </div>
        </div>
        <div className="chat-header-right">
          <button className="header-pill" onClick={() => setMessages(initialMessages)}>
            New Chat
          </button>
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
            disabled={isLoading}
          />
          <button
            onClick={sendMessage}
            className="send-btn"
            aria-label="Send message"
            disabled={isLoading}
          >
            <Send size={18} />
          </button>
        </div>
      </footer>
    </div>
  );
}
