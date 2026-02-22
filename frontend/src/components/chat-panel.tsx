"use client";

import { useState, useRef, useEffect } from "react";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

interface ChatPanelProps {
  projectId?: string;
}

export function ChatPanel({ projectId }: ChatPanelProps) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [toolCalls, setToolCalls] = useState<string[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, toolCalls]);

  async function sendMessage() {
    if (!input.trim() || loading) return;

    const userMsg: ChatMessage = { role: "user", content: input.trim() };
    const updated = [...messages, userMsg];
    setMessages(updated);
    setInput("");
    setLoading(true);
    setToolCalls([]);

    try {
      const apiMessages = updated.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_id: projectId || "PORTFOLIO",
          messages: apiMessages,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        setMessages([
          ...updated,
          {
            role: "assistant",
            content: err.reply || err.error || "Something went wrong.",
          },
        ]);
        return;
      }

      // Read SSE stream
      const reader = res.body?.getReader();
      if (!reader) return;

      const decoder = new TextDecoder();
      let assistantText = "";
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const data = line.slice(6);
          try {
            const parsed = JSON.parse(data);
            if (parsed.type === "text") {
              assistantText += parsed.content;
              setMessages([
                ...updated,
                { role: "assistant", content: assistantText },
              ]);
            } else if (parsed.type === "tool_call") {
              setToolCalls((prev) => [
                ...prev,
                `${parsed.name}(${JSON.stringify(parsed.input)})`,
              ]);
            } else if (parsed.type === "done") {
              // stream complete
            }
          } catch {
            // skip unparseable lines
          }
        }
      }

      if (assistantText) {
        setMessages([
          ...updated,
          { role: "assistant", content: assistantText },
        ]);
      }
    } catch (err) {
      setMessages([
        ...updated,
        {
          role: "assistant",
          content: "Connection error. Is the backend running?",
        },
      ]);
    } finally {
      setLoading(false);
      setToolCalls([]);
    }
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 w-14 h-14 bg-blue-600 hover:bg-blue-700 rounded-full shadow-lg flex items-center justify-center transition-colors z-50"
        title="Open AI Chat"
      >
        <svg
          className="w-6 h-6 text-white"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
          />
        </svg>
      </button>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 w-96 h-[32rem] bg-gray-900 border border-gray-700 rounded-xl shadow-2xl flex flex-col z-50">
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-gray-700">
        <div>
          <h3 className="font-semibold text-sm">AI Assistant</h3>
          <span className="text-xs text-gray-400">
            {projectId ? `Project: ${projectId}` : "Portfolio"}
          </span>
        </div>
        <button
          onClick={() => setOpen(false)}
          className="text-gray-400 hover:text-white p-1"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 space-y-3">
        {messages.length === 0 && (
          <div className="text-sm text-gray-500 text-center mt-8">
            <p className="mb-2">Ask me about this project&apos;s financials.</p>
            <div className="space-y-1 text-xs text-gray-600">
              <p>&quot;What&apos;s causing the labor overruns?&quot;</p>
              <p>&quot;Show me the change orders&quot;</p>
              <p>&quot;What if we recover 10% of labor costs?&quot;</p>
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`text-sm ${
              msg.role === "user"
                ? "ml-8 bg-blue-600/20 border border-blue-500/30 rounded-lg p-2.5"
                : "mr-4 bg-gray-800 rounded-lg p-2.5"
            }`}
          >
            <div className="text-xs text-gray-500 mb-1">
              {msg.role === "user" ? "You" : "AI Agent"}
            </div>
            <div className="whitespace-pre-wrap">{msg.content}</div>
          </div>
        ))}

        {/* Tool call indicators */}
        {toolCalls.length > 0 && (
          <div className="text-xs text-gray-500 bg-gray-800/50 rounded p-2 space-y-1">
            {toolCalls.map((tc, i) => (
              <div key={i} className="flex items-center gap-1">
                <span className="text-blue-400">&#9881;</span> {tc}
              </div>
            ))}
          </div>
        )}

        {loading && toolCalls.length === 0 && (
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <span className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full" />
            Thinking...
          </div>
        )}
      </div>

      {/* Input */}
      <div className="p-3 border-t border-gray-700">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && sendMessage()}
            placeholder="Ask about this project..."
            disabled={loading}
            className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500 disabled:opacity-50"
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="px-3 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 rounded-lg text-sm transition-colors"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
