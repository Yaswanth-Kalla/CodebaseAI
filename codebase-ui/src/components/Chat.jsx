import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// ─────────────────────────────────────────────────────────────────
// MARKDOWN SAFETY NET
// Backend prompt now enforces proper markdown — this is light cleanup only.
// ─────────────────────────────────────────────────────────────────
function normalizeToMarkdown(raw) {
  if (!raw) return "";

  let text = raw;

  // Remove stray backticks
  text = text.replace(/^\s*`\s*$/gm, "");

  // Fix broken words across lines (VERY IMPORTANT)
  text = text.replace(/([a-z])\n([a-z])/g, "$1 $2");

  // Remove fake code blocks (non-code)
  text = text.replace(/```[\s\S]*?```/g, (block) => {
    const inner = block.replace(/```[\w]*\n?|```/g, "");

    const looksLikeCode =
      /[{}();]/.test(inner) ||
      /\b(def|class|function|return|if|for|import)\b/.test(inner);

    return looksLikeCode ? block : inner;
  });

  // Clean spacing
  text = text.replace(/\n{3,}/g, "\n\n");

  return text.trim();
}

// ─── Copy hook ────────────────────────────────────────────────
function useCopy(defaultText) {
  const [copied, setCopied] = useState(false);
  const copy = (override) => {
    navigator.clipboard.writeText(override ?? defaultText);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };
  return { copied, copy };
}

// ─── Code block component ─────────────────────────────────────
function CodeBlock({ language, value }) {
  const { copied, copy } = useCopy(value);
  return (
    <div className="my-4 rounded-xl overflow-hidden border border-white/10 bg-[#060A14]">
      <div className="flex items-center justify-between px-4 py-2 bg-white/4 border-b border-white/8">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-red-500/60" />
          <span className="w-2 h-2 rounded-full bg-yellow-500/60" />
          <span className="w-2 h-2 rounded-full bg-green-500/60" />
          <span className="ml-2 text-[10px] font-mono text-gray-500 uppercase tracking-wider">
            {language || "plaintext"}
          </span>
        </div>
        <button
          onClick={() => copy()}
          className="flex items-center gap-1.5 text-[10px] text-gray-500 hover:text-gray-200 transition-colors px-2 py-1 rounded hover:bg-white/5"
        >
          {copied ? <span className="text-emerald-400 font-medium">✓ Copied!</span> : <span>⧉ Copy</span>}
        </button>
      </div>
      <pre className="overflow-x-auto px-5 py-4 text-[12.5px] leading-[1.7] font-mono text-gray-200 whitespace-pre">
        <code>{value}</code>
      </pre>
    </div>
  );
}

// ─── Markdown components ──────────────────────────────────────
const MD = {
  p({ children }) {
    return <p className="mb-3 last:mb-0 leading-[1.85] text-gray-200 text-[13.5px]">{children}</p>;
  },
  h1({ children }) {
    return (
      <h1 className="text-white font-semibold text-[15px] mt-6 mb-3 pb-2 border-b border-white/8 flex items-center gap-2">
        {children}
      </h1>
    );
  },
  h2({ children }) {
    return <h2 className="text-white font-semibold text-[13.5px] mt-5 mb-2">{children}</h2>;
  },
  h3({ children }) {
    return <h3 className="text-gray-300 font-medium text-[13px] mt-4 mb-1.5">{children}</h3>;
  },
  ul({ children }) {
    return <ul className="my-2.5 ml-1 space-y-1.5 text-gray-200 text-[13.5px]">{children}</ul>;
  },
  ol({ children }) {
    return <ol className="my-2.5 ml-1 space-y-1.5 text-gray-200 text-[13.5px] list-decimal list-inside">{children}</ol>;
  },
  li({ children }) {
    return (
      <li className="flex items-start gap-2 leading-relaxed">
        <span className="mt-[5px] w-1.5 h-1.5 rounded-full bg-violet-400/70 shrink-0" />
        <span>{children}</span>
      </li>
    );
  },
  strong({ children }) {
    return <strong className="text-white font-semibold">{children}</strong>;
  },
  em({ children }) {
    return <em className="text-gray-300 not-italic border-b border-dotted border-gray-600">{children}</em>;
  },
  hr() {
    return <hr className="my-5 border-white/8" />;
  },
  blockquote({ children }) {
    return (
      <blockquote className="my-3 border-l-[3px] border-violet-500/50 pl-4 bg-violet-500/5 py-2 pr-3 rounded-r-xl text-gray-400 text-[13px]">
        {children}
      </blockquote>
    );
  },
  // ── Core fix: smart inline vs block code ────────────────────
  code({ node, inline, className, children, ...props }) {
    const raw = String(children).replace(/\n$/, "");
    const lang = /language-(\w+)/.exec(className || "")?.[1] || "";

    // Treat as block if: has explicit language, has newlines, or is a long snippet
    const isBlock =
  !inline &&
  (
    lang ||
    /\n/.test(raw) ||
    /[{}();]/.test(raw) ||
    /\b(def|class|function|return|if|for|import)\b/.test(raw)
  );

    if (isBlock) return <CodeBlock language={lang} value={raw} />;

    // Inline code — filenames, identifiers, short snippets
    return (
      <code
        className="bg-violet-950/60 text-violet-300 font-mono text-[11.5px] px-1.5 py-0.5 rounded border border-violet-500/20 mx-0.5"
        {...props}
      >
        {raw}
      </code>
    );
  },
  // Tables
  table({ children }) {
    return (
      <div className="my-4 overflow-x-auto rounded-xl border border-white/8">
        <table className="w-full text-[13px] text-gray-300 border-collapse">{children}</table>
      </div>
    );
  },
  thead({ children }) {
    return <thead className="bg-white/5 text-white text-[11px] uppercase tracking-wider">{children}</thead>;
  },
  th({ children }) {
    return <th className="px-4 py-2.5 text-left font-medium border-b border-white/8">{children}</th>;
  },
  td({ children }) {
    return <td className="px-4 py-2.5 border-b border-white/5">{children}</td>;
  },
};

// ─── Message bubble ───────────────────────────────────────────
// KEY: while msg.streaming=true, render plain text to avoid
// ReactMarkdown treating incomplete chunks as broken code blocks.
// Once streaming stops, swap to full markdown render.
function MessageBubble({ msg }) {
  const { copied, copy } = useCopy(msg.text);
  const isUser = msg.role === "user";

  const renderContent = () => {
    if (isUser) {
      return <p className="whitespace-pre-wrap leading-relaxed text-[13.5px]">{msg.text}</p>;
    }
    if (msg.streaming) {
      // Plain text while streaming — no markdown parsing on partial chunks
      return (
        <p className="whitespace-pre-wrap leading-relaxed text-[13.5px] text-gray-300">
          {msg.text}
        </p>
      );
    }
    // Full markdown render only when complete
    return (
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={MD}>
  {normalizeToMarkdown(msg.text)
    .replace(/\s+/g, " ")
    .replace(/\.\s+/g, ".\n\n")}
</ReactMarkdown>
    );
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, ease: "easeOut" }}
      className={`flex items-start gap-3 ${isUser ? "flex-row-reverse" : ""}`}
    >
      {!isUser && (
        <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-violet-500 to-blue-600 flex items-center justify-center text-xs shrink-0 mt-0.5 shadow-lg shadow-violet-900/50">
          ⬡
        </div>
      )}

      <div className={`relative group text-sm ${
        isUser
          ? "bg-violet-600 text-white px-4 py-2.5 rounded-2xl rounded-tr-sm max-w-[65%] shadow-lg shadow-violet-900/20"
          : "bg-[#0C1120] border border-white/6 text-gray-200 px-5 py-4 rounded-2xl rounded-tl-sm max-w-[90%] w-full"
      }`}>
        {!isUser && (
          <button
            onClick={() => copy()}
            className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 flex items-center gap-1 text-[10px] text-gray-600 hover:text-gray-300 bg-white/4 hover:bg-white/8 px-2 py-1 rounded transition-all"
          >
            {copied ? <span className="text-emerald-400">✓ Copied</span> : "⧉ Copy"}
          </button>
        )}
        {renderContent()}
      </div>
    </motion.div>
  );
}

// ─── Main Chat export ─────────────────────────────────────────
export default function Chat({ setHistory, chatStore, setChatStore, selectedQuery, setFileToOpen }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef(null);
  const inputRef = useRef(null);

  const [showUpload, setShowUpload] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [repoUrl, setRepoUrl] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState("");
  const [uploadSuccess, setUploadSuccess] = useState(false);

  const fetchFiles = async () => {
    try { await fetch("https://codebaseai-orv6.onrender.com/files"); }
    catch (e) { console.error("fetchFiles error", e); }
  };

  useEffect(() => { fetchFiles(); }, []);

  useEffect(() => {
    if (selectedQuery && chatStore[selectedQuery]) {
      setMessages(chatStore[selectedQuery]);
    }
  }, [selectedQuery]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const onUploadSuccess = () => {
    setMessages(prev => [
      ...prev,
      { role: "bot", text: "✅ Repository uploaded and indexed. You can now ask questions about your codebase." }
    ]);
    setTimeout(() => { setShowUpload(false); fetchFiles(); }, 900);
  };

  const handleZipUpload = async (file) => {
    if (!file) return;
    setUploading(true); setUploadSuccess(false); setUploadStatus("Uploading ZIP...");
    const fd = new FormData();
    fd.append("file", file);
    try {
      const res = await fetch("https://codebaseai-orv6.onrender.com/upload-zip", { method: "POST", body: fd });
      const data = await res.json();
      setUploadStatus(data.status || "Upload complete");
      setUploadSuccess(true); onUploadSuccess();
    } catch { setUploadStatus("Upload failed — is the backend running?"); }
    setUploading(false);
  };

  const handleGithubUpload = async () => {
    if (!repoUrl.trim()) return;
    setUploading(true); setUploadSuccess(false); setUploadStatus("Cloning repository...");
    try {
      const res = await fetch("https://codebaseai-orv6.onrender.com/upload-github", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_url: repoUrl }),
      });
      const data = await res.json();
      setUploadStatus(data.status || "Clone complete");
      setUploadSuccess(true); onUploadSuccess();
    } catch { setUploadStatus("Clone failed — check URL or backend"); }
    setUploading(false);
  };

  const handleDrop = (e) => {
    e.preventDefault(); setDragActive(false);
    handleZipUpload(e.dataTransfer.files[0]);
  };

  const sendMessage = async (customQuery = null) => {
    const query = customQuery || input;
    if (!query.trim() || loading) return;

    setLoading(true);
    setHistory(prev => [...prev, query]);
    setMessages(prev => [...prev, { role: "user", text: query }]);
    setInput("");
    inputRef.current?.focus();

    const endpoint = customQuery === "Summarize Codebase"
      ? "https://codebaseai-orv6.onrender.com/summarize-stream"
      : "https://codebaseai-orv6.onrender.com/chat-stream";

    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let streamed = "";

      // Mark as streaming=true — MessageBubble renders plain text while this is true
      setMessages(prev => [...prev, { role: "bot", text: "", streaming: true }]);

      let buffer = "";

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  buffer += decoder.decode(value);

  const lines = buffer.split("\n");
  buffer = lines.pop(); // keep incomplete chunk

  for (const line of lines) {
    if (!line.startsWith("data:")) continue;

    const token = line.slice(5);
    if (!token || token.startsWith("__FILES__")) continue;

    streamed += token;

    setMessages(prev => {
      const updated = [...prev];
      updated[updated.length - 1] = {
        role: "bot",
        text: streamed,
        streaming: true
      };
      return updated;
    });
  }
}

      // Streaming done — flip streaming=false so markdown renders properly
      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = { role: "bot", text: streamed, streaming: false };
        return updated;
      });

      setChatStore(prev => ({
        ...prev,
        [query]: [{ role: "user", text: query }, { role: "bot", text: streamed }],
      }));
    } catch (err) {
      console.error("Stream error:", err);
      setMessages(prev => {
        const u = [...prev];
        u[u.length - 1] = {
          role: "bot",
          text: "⚠️ Could not reach the backend. Make sure it's running on **port 8000**.",
        };
        return u;
      });
    }
    setLoading(false);
  };

  const SUGGESTED = [
    { icon: "📋", label: "Summarize the codebase" },
    { icon: "🧩", label: "What are the main modules?" },
    { icon: "🔌", label: "Show me the API endpoints" },
    { icon: "🌊", label: "Explain the data flow" },
  ];

  return (
    <div className="flex h-full flex-col bg-[#070B14]">

      {/* ── HEADER ── */}
      <div className="h-14 border-b border-white/5 flex items-center justify-between px-6 shrink-0 bg-[#070B14]">
        <div className="flex items-center gap-2.5">
          <span className="text-white font-semibold text-sm">Chat</span>
          <AnimatePresence>
            {loading && (
              <motion.div
                initial={{ opacity: 0, x: -4 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }}
                className="flex items-center gap-1.5 text-[10px] text-violet-400"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-pulse" />
                streaming
              </motion.div>
            )}
          </AnimatePresence>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => { setShowUpload(true); setUploadStatus(""); setUploadSuccess(false); }}
            className="flex items-center gap-1.5 bg-white/5 hover:bg-white/8 border border-white/8 px-3.5 py-1.5 rounded-lg text-xs text-gray-400 hover:text-white transition-all"
          >
            ⬆ Upload Repo
          </button>
          <button
            onClick={() => sendMessage("Summarize Codebase")}
            disabled={loading}
            className="flex items-center gap-1.5 bg-violet-600 hover:bg-violet-500 disabled:opacity-40 px-3.5 py-1.5 rounded-lg text-xs text-white font-medium transition-all shadow-lg shadow-violet-900/40"
          >
            ⚡ Summarize
          </button>
        </div>
      </div>

      {/* ── EMPTY STATE ── */}
      {messages.length === 0 && (
        <div className="flex-1 flex flex-col items-center justify-center gap-8 px-6">
          <div className="text-center space-y-2.5">
            <div className="w-14 h-14 mx-auto rounded-2xl bg-gradient-to-br from-violet-500 to-blue-600 flex items-center justify-center text-2xl shadow-xl shadow-violet-900/40 mb-4">⬡</div>
            <h2 className="text-xl text-white font-semibold">Ask anything about your codebase</h2>
            <p className="text-gray-500 text-sm max-w-sm leading-relaxed">
              Upload a repo, then explore it with natural language — functions, files, architecture, anything.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-2 w-full max-w-md">
            {SUGGESTED.map((q, i) => (
              <button
                key={i}
                onClick={() => sendMessage(q.label)}
                className="text-left bg-white/3 hover:bg-white/6 border border-white/6 hover:border-violet-500/30 rounded-xl px-4 py-3.5 transition-all group"
              >
                <span className="text-lg block mb-1.5">{q.icon}</span>
                <span className="text-[12px] text-gray-400 group-hover:text-gray-200 transition-colors leading-snug">{q.label}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── MESSAGES ── */}
      {messages.length > 0 && (
        <div className="flex-1 overflow-y-auto px-5 py-6 space-y-6">
          {messages.map((msg, i) => <MessageBubble key={i} msg={msg} />)}

          {/* Typing dots */}
          {loading && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-center gap-3">
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-violet-500 to-blue-600 flex items-center justify-center text-xs shrink-0 shadow-lg shadow-violet-900/40">⬡</div>
              <div className="bg-[#0C1120] border border-white/6 rounded-2xl rounded-tl-sm px-5 py-4 flex gap-1.5 items-center">
                {[0, 1, 2].map(n => (
                  <span
                    key={n}
                    className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-bounce"
                    style={{ animationDelay: `${n * 0.15}s` }}
                  />
                ))}
              </div>
            </motion.div>
          )}
          <div ref={chatEndRef} />
        </div>
      )}

      {/* ── INPUT ── */}
      <div className="px-5 pb-5 pt-3 border-t border-white/5 shrink-0">
        <div className="flex gap-2 bg-[#0C1120] border border-white/8 rounded-2xl px-4 py-2.5 focus-within:border-violet-500/40 transition-colors">
          <input
            ref={inputRef}
            className="flex-1 bg-transparent outline-none text-[13.5px] text-white placeholder-gray-600 py-0.5"
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="Ask about your codebase..."
            onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
          />
          <button
            onClick={() => sendMessage()}
            disabled={!input.trim() || loading}
            className="bg-violet-600 hover:bg-violet-500 disabled:opacity-30 disabled:cursor-not-allowed text-white px-4 py-1.5 rounded-xl text-xs font-medium transition-all"
          >
            {loading ? "···" : "Send ➤"}
          </button>
        </div>
        <p className="text-center text-gray-700 text-[10px] mt-2">Enter to send · Shift+Enter for newline</p>
      </div>

      {/* ── UPLOAD MODAL ── */}
      <AnimatePresence>
        {showUpload && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/75 backdrop-blur-md flex items-center justify-center z-50"
            onClick={e => e.target === e.currentTarget && setShowUpload(false)}
          >
            <motion.div
              initial={{ scale: 0.96, opacity: 0, y: 10 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.96, opacity: 0, y: 10 }}
              transition={{ duration: 0.16 }}
              className="bg-[#0C1120] border border-white/8 rounded-2xl p-6 w-[440px] shadow-2xl shadow-black/70"
            >
              <div className="flex items-start justify-between mb-5">
                <div>
                  <h2 className="text-white font-semibold text-[15px]">Upload Repository</h2>
                  <p className="text-gray-500 text-xs mt-0.5">ZIP file or public GitHub URL</p>
                </div>
                <button onClick={() => setShowUpload(false)} className="text-gray-600 hover:text-gray-300 text-xl leading-none transition-colors mt-0.5">✕</button>
              </div>

              <div
                onDrop={handleDrop}
                onDragOver={e => { e.preventDefault(); setDragActive(true); }}
                onDragLeave={() => setDragActive(false)}
                className={`border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer ${
                  dragActive ? "border-violet-500 bg-violet-500/8" : "border-white/10 hover:border-white/20 hover:bg-white/2"
                }`}
              >
                <div className="text-4xl mb-2">📦</div>
                <p className="text-gray-300 text-sm font-medium">Drop your ZIP here</p>
                <p className="text-gray-600 text-xs mt-1 mb-4">or click to browse files</p>
                <label className="cursor-pointer bg-white/6 hover:bg-white/10 border border-white/10 rounded-lg px-4 py-2 text-xs text-gray-300 transition-all">
                  Browse ZIP
                  <input type="file" accept=".zip" className="hidden" onChange={e => handleZipUpload(e.target.files[0])} />
                </label>
              </div>

              <div className="flex items-center gap-3 my-4">
                <div className="flex-1 h-px bg-white/6" />
                <span className="text-gray-600 text-[11px]">or import from GitHub</span>
                <div className="flex-1 h-px bg-white/6" />
              </div>

              <div className="space-y-2">
                <input
                  type="text" placeholder="https://github.com/user/repo"
                  value={repoUrl} onChange={e => setRepoUrl(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && handleGithubUpload()}
                  className="w-full bg-white/4 border border-white/8 rounded-xl px-4 py-2.5 text-sm text-white placeholder-gray-600 outline-none focus:border-violet-500/50 transition-colors"
                />
                <button
                  onClick={handleGithubUpload}
                  disabled={uploading || !repoUrl.trim()}
                  className="w-full bg-violet-600 hover:bg-violet-500 disabled:opacity-40 disabled:cursor-not-allowed py-2.5 rounded-xl text-sm font-medium transition-all"
                >
                  {uploading ? "Processing..." : "Clone from GitHub"}
                </button>
              </div>

              {uploadStatus && (
                <motion.div
                  initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }}
                  className={`mt-4 flex items-center gap-2 px-4 py-3 rounded-xl text-xs border ${
                    uploadSuccess ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                    : uploading ? "bg-blue-500/10 border-blue-500/20 text-blue-400"
                    : "bg-red-500/10 border-red-500/20 text-red-400"
                  }`}
                >
                  <span>{uploading ? "⏳" : uploadSuccess ? "✅" : "❌"}</span>
                  <span>{uploadStatus}</span>
                </motion.div>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
