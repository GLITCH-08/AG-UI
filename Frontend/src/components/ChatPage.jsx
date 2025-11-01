import React, { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Bot, Sparkles, Wrench, CheckCircle } from "lucide-react";
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
  const [currentStatus, setCurrentStatus] = useState("online");
  const [toolCalls, setToolCalls] = useState([]);
  const bottomRef = useRef(null);
 
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, toolCalls]);
 
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
    setCurrentStatus("thinking...");
    setToolCalls([]);
 
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
     
      let messageAdded = false;
      let buffer = "";
 
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
 
        buffer += decoder.decode(value, { stream: true });
 
        const parts = buffer.split("\n");
        buffer = parts.pop() || "";
 
        for (const part of parts) {
          if (part.startsWith("data: ")) {
            const data = part.slice(6);
            try {
              const event = JSON.parse(data);
              console.log("📦 Event received:", event.type, event);
 
              switch (event.type) {
                case "RUN_STARTED":
                  console.log("🏁 Run started");
                  setCurrentStatus("processing...");
                  break;
 
                case "TEXT_MESSAGE_START":
                  console.log("💬 Message stream starting");
                  setCurrentStatus("typing...");
                  if (!messageAdded) {
                    setMessages((prev) => [...prev, assistantMsg]);
                    messageAdded = true;
                  }
                  break;
 
                case "TEXT_MESSAGE_CONTENT":
                  // Append streamed text character by character
                  console.log(`📝 Received char: "${event.delta}"`);
                  assistantMsg.content += event.delta;
                  setMessages((prev) => {
                    const updated = [...prev];
                    const lastIndex = updated.length - 1;
                    if (lastIndex >= 0 && updated[lastIndex].role === "assistant") {
                      updated[lastIndex] = { ...assistantMsg };
                    }
                    return updated;
                  });
                  break;
 
                case "TEXT_MESSAGE_END":
                  console.log("✅ Message stream ended");
                  setCurrentStatus("online");
                  break;
 
                case "TOOL_CALL_START":
                  console.log("🔧 Tool call started:", event.toolCallName);
                  setCurrentStatus(`calling ${event.toolCallName}...`);
                  setToolCalls((prev) => [
                    ...prev,
                    {
                      id: event.tool_call_id,
                      name: event.toolCallName,
                      args: "",
                      result: "",
                      status: "calling",
                    },
                  ]);
                  break;
 
                case "TOOL_CALL_ARGS":
                  console.log("📝 Tool args:", event.delta);
                  setToolCalls((prev) =>
                    prev.map((tc) =>
                      tc.id === event.tool_call_id
                        ? { ...tc, args: event.delta }
                        : tc
                    )
                  );
                  break;
 
                case "TOOL_CALL_RESULT":
                  console.log("✅ Tool result:", event.content);
                  setToolCalls((prev) =>
                    prev.map((tc) =>
                      tc.id === event.tool_call_id
                        ? { ...tc, result: event.content, status: "completed" }
                        : tc
                    )
                  );
                  setCurrentStatus("processing results...");
                  break;
 
                case "RUN_FINISHED":
                  console.log("🏁 Run finished");
                  setCurrentStatus("online");
                  setIsLoading(false);
                  break;
 
                case "RUN_ERROR":
                  console.error("❌ Run error:", event.message);
                  setCurrentStatus("error");
                  setIsLoading(false);
                  if (!messageAdded) {
                    setMessages((prev) => [
                      ...prev,
                      {
                        id: Date.now() + 2,
                        role: "assistant",
                        content: `Error: ${event.message}`,
                        time: new Date().toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        }),
                      },
                    ]);
                  }
                  break;
 
                default:
                  console.log("❓ Unknown event type:", event.type);
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
      setCurrentStatus("error");
    } finally {
      setIsLoading(false);
      setCurrentStatus("online");
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
              <Sparkles size={13} /> {currentStatus}
            </div>
          </div>
        </div>
        <div className="chat-header-right">
          <button
            className="header-pill"
            onClick={() => {
              setMessages(initialMessages);
              setToolCalls([]);
              setCurrentStatus("online");
            }}
          >
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
              <MessageBubble
                role={msg.role}
                content={msg.content}
                time={msg.time}
              />
            </motion.div>
          ))}
        </AnimatePresence>
 
        {/* Tool Call Status Display */}
        {toolCalls.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="tool-calls-container"
            style={{
              background: "#f0f4ff",
              borderRadius: "12px",
              padding: "12px 16px",
              marginTop: "8px",
              border: "1px solid #d0d9ff",
            }}
          >
            <div
              style={{
                fontSize: "0.75rem",
                fontWeight: "600",
                color: "#4f46e5",
                marginBottom: "8px",
                display: "flex",
                alignItems: "center",
                gap: "6px",
              }}
            >
              <Wrench size={14} />
              Tool Calls
            </div>
            {toolCalls.map((tc) => (
              <div
                key={tc.id}
                style={{
                  background: "white",
                  borderRadius: "8px",
                  padding: "8px 10px",
                  marginBottom: "6px",
                  fontSize: "0.72rem",
                  border: "1px solid #e0e7ff",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                    marginBottom: "4px",
                  }}
                >
                  {tc.status === "completed" ? (
                    <CheckCircle size={12} color="#10b981" />
                  ) : (
                    <div
                      style={{
                        width: "12px",
                        height: "12px",
                        border: "2px solid #4f46e5",
                        borderTopColor: "transparent",
                        borderRadius: "50%",
                        animation: "spin 0.8s linear infinite",
                      }}
                    />
                  )}
                  {/* tool name */}
                  <strong style={{ color: "#1e293b" }}>{tc.name}</strong> 
                </div>
                {/* {tc.args && (
                  <div style={{ color: "#64748b", marginLeft: "18px" }}>
                    Args: {tc.args}
                  </div>
                )} */}
                {tc.result && (
                  <div
                    style={{
                      color: "#059669",
                      marginLeft: "18px",
                      marginTop: "4px",
                    }}
                  >
                    Result: {tc.result}
                  </div>
                )}
              </div>
            ))}
          </motion.div>
        )}
 
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
 
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}