import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";

export default function Chat({ setHistory, chatStore, setChatStore, selectedQuery, setFileToOpen }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef(null);

  // Upload modal state
  const [showUpload, setShowUpload] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [repoUrl, setRepoUrl] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState("");
  const [uploadSuccess, setUploadSuccess] = useState(false);

  // Fetch files on mount (kept for sidebar file list sync)
  const fetchFiles = async () => {
    try {
      await fetch("http://localhost:8000/files");
    } catch (e) {
      console.error("Failed to fetch files", e);
    }
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
    { role: "bot", text: "✅ Repository uploaded successfully. Ready to analyze." }
  ]);

  setTimeout(() => {
    setShowUpload(false);
    fetchFiles(); // refresh file list
  }, 800);
};

  // ── ZIP UPLOAD ──────────────────────────────────────────────
  const handleZipUpload = async (file) => {
    if (!file) return;
    setUploading(true);
    setUploadSuccess(false);
    setUploadStatus("Uploading ZIP...");
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await fetch("http://localhost:8000/upload-zip", { method: "POST", body: formData });
      const data = await res.json();
      setUploadStatus(data.status || "Upload complete");
      setUploadSuccess(true);
      onUploadSuccess();
    } catch {
      setUploadStatus("Upload failed — check backend");
      setUploadSuccess(false);
    }
    setUploading(false);
  };

  // ── GITHUB UPLOAD ───────────────────────────────────────────
  const handleGithubUpload = async () => {
    if (!repoUrl.trim()) return;
    setUploading(true);
    setUploadSuccess(false);
    setUploadStatus("Cloning repository...");
    try {
      const res = await fetch("http://localhost:8000/upload-github", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_url: repoUrl }),
      });
      const data = await res.json();
      setUploadStatus(data.status || "Clone complete");
      setUploadSuccess(true);
      onUploadSuccess();
    } catch {
      setUploadStatus("Clone failed — check URL or backend");
      setUploadSuccess(false);
    }
    setUploading(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    handleZipUpload(e.dataTransfer.files[0]);
  };

  // ── SEND MESSAGE ─────────────────────────────────────────────
  const sendMessage = async (customQuery = null) => {
    const query = customQuery || input;
    if (!query.trim()) return;

    setLoading(true);
    setHistory(prev => [...prev, query]);
    setMessages(prev => [...prev, { role: "user", text: query }]);
    setInput("");

    const endpoint = query.toLowerCase().includes("summarise")
      ? "http://localhost:8000/summarize-stream"
      : "http://localhost:8000/chat-stream";

    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // FIX: always send a JSON body
        body: JSON.stringify({ query }),
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let streamed = "";

      setMessages(prev => [...prev, { role: "bot", text: "" }]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        for (let line of chunk.split("\n")) {
          if (!line.startsWith("data:")) continue;
          const cleaned = line.replace("data:", "");

          // Handle file list update from stream
          if (cleaned.startsWith("__FILES__")) {
            try {
              // file list update — no action needed in chat
            } catch {}
            continue;
          }

          streamed += cleaned;
          setMessages(prev => {
            const updated = [...prev];
            updated[updated.length - 1] = { role: "bot", text: streamed };
            return updated;
          });
        }
      }

      setChatStore(prev => ({
        ...prev,
        [query]: [
          { role: "user", text: query },
          { role: "bot", text: streamed },
        ],
      }));
    } catch (err) {
      console.error("Stream error:", err);
      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: "bot",
          text: "⚠️ Failed to reach backend. Is it running on port 8000?",
        };
        return updated;
      });
    }

    setLoading(false);
  };

  const copyText = (text) => navigator.clipboard.writeText(text);

  const SUGGESTED = [
    "Summarize the codebase",
    "What are the main modules?",
    "Show me the API endpoints",
    "Explain the data flow",
  ];

  return (
    <div className="flex h-full flex-col bg-[#070B14]">

      {/* HEADER */}
      <div className="h-14 border-b border-white/5 flex items-center justify-between px-6 shrink-0">
        <div className="flex items-center gap-2.5">
          <span className="text-white font-semibold text-sm">Chat</span>
          {loading && (
            <span className="text-[10px] text-violet-400 animate-pulse">● streaming</span>
          )}
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => { setShowUpload(true); setUploadStatus(""); setUploadSuccess(false); }}
            className="flex items-center gap-1.5 bg-white/5 hover:bg-white/10 border border-white/8 px-3 py-1.5 rounded-lg text-xs text-gray-300 transition-all"
          >
            <span>⬆</span> Upload Repo
          </button>
          <button
            onClick={() => sendMessage("Summarize Codebase")}
            disabled={loading}
            className="flex items-center gap-1.5 bg-violet-600/80 hover:bg-violet-600 px-3 py-1.5 rounded-lg text-xs text-white transition-all disabled:opacity-40"
          >
            <span>⚡</span> Summarize
          </button>
        </div>
      </div>

      {/* EMPTY STATE */}
      {messages.length === 0 && (
        <div className="flex-1 flex flex-col items-center justify-center gap-8 px-6">
          <div className="text-center space-y-2">
            <div className="text-4xl mb-3">⬡</div>
            <h2 className="text-xl text-white font-semibold">Ask anything about your codebase</h2>
            <p className="text-gray-500 text-sm">Upload a repo, then start exploring with natural language</p>
          </div>
          <div className="grid grid-cols-2 gap-2 w-full max-w-md">
            {SUGGESTED.map((q, i) => (
              <button
                key={i}
                onClick={() => sendMessage(q)}
                className="text-left text-xs bg-white/4 hover:bg-white/8 border border-white/6 rounded-xl px-4 py-3 text-gray-400 hover:text-gray-200 transition-all"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* MESSAGES */}
      {messages.length > 0 && (
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-5">
          {messages.map((msg, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              {msg.role === "bot" && (
                <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-violet-500 to-blue-500 flex items-center justify-center text-xs mr-2.5 mt-0.5 shrink-0">⬡</div>
              )}
              <div
                className={`relative group rounded-2xl text-sm leading-relaxed
                  ${msg.role === "user"
                    ? "bg-violet-600/90 text-white px-4 py-2.5 max-w-[68%]"
                    : "bg-white/5 border border-white/6 text-gray-200 px-5 py-4 max-w-[84%] w-full"
                  }`}
              >
                {/* Copy button */}
                <button
                  onClick={() => copyText(msg.text)}
                  className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition text-gray-500 hover:text-gray-300 text-xs"
                  title="Copy"
                >
                  ⧉
                </button>

                {msg.role === "bot" ? (
                  <ReactMarkdown
                    components={{
                      p: ({ children }) => <p className="mb-3 last:mb-0 leading-relaxed">{children}</p>,
                      h1: ({ children }) => <h1 className="text-white font-semibold text-base mb-2 mt-4">{children}</h1>,
                      h2: ({ children }) => <h2 className="text-white font-semibold text-sm mb-2 mt-3">{children}</h2>,
                      h3: ({ children }) => <h3 className="text-gray-300 font-medium text-sm mb-1.5 mt-3">{children}</h3>,
                      ul: ({ children }) => <ul className="space-y-1 mb-3 ml-4 list-disc list-outside text-gray-300">{children}</ul>,
                      ol: ({ children }) => <ol className="space-y-1 mb-3 ml-4 list-decimal list-outside text-gray-300">{children}</ol>,
                      li: ({ children }) => <li className="leading-relaxed">{children}</li>,
                      strong: ({ children }) => <strong className="text-white font-semibold">{children}</strong>,
                      code({ inline, children }) {
                        const text = String(children);
                        if (inline) {
                          return (
                            <code className="bg-white/8 text-violet-300 font-mono text-xs px-1.5 py-0.5 rounded">
                              {text}
                            </code>
                          );
                        }
                        return (
                          <div className="bg-black/50 border border-white/8 rounded-xl mt-2 mb-3 overflow-x-auto">
                            <pre className="text-xs text-gray-300 font-mono p-4 whitespace-pre">{text}</pre>
                          </div>
                        );
                      },
                    }}
                  >
                    {(msg.text || "").replace(/\n/g, "\n\n")}
                  </ReactMarkdown>
                ) : (
                  <p className="whitespace-pre-wrap">{msg.text}</p>
                )}
              </div>
            </motion.div>
          ))}

          {loading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex justify-start items-center gap-2"
            >
              <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-violet-500 to-blue-500 flex items-center justify-center text-xs shrink-0">⬡</div>
              <div className="bg-white/5 border border-white/6 rounded-2xl px-5 py-3 flex gap-1.5 items-center">
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

      {/* INPUT */}
      <div className="p-4 border-t border-white/5 shrink-0">
        <div className="flex gap-2 bg-white/4 border border-white/8 rounded-2xl px-4 py-2 focus-within:border-violet-500/40 transition-colors">
          <input
            className="flex-1 bg-transparent outline-none text-sm text-white placeholder-gray-600 py-1"
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="Ask about your codebase..."
            onKeyDown={e => e.key === "Enter" && !e.shiftKey && sendMessage()}
          />
          <button
            onClick={() => sendMessage()}
            disabled={!input.trim() || loading}
            className="bg-violet-600 hover:bg-violet-500 disabled:opacity-30 disabled:cursor-not-allowed text-white px-3.5 py-1.5 rounded-xl text-xs font-medium transition-all"
          >
            {loading ? "..." : "Send ➤"}
          </button>
        </div>
        <p className="text-center text-gray-700 text-[10px] mt-2">Enter to send · Shift+Enter for newline</p>
      </div>

      {/* ── UPLOAD MODAL ─────────────────────────────────────── */}
      <AnimatePresence>
        {showUpload && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50"
            onClick={e => e.target === e.currentTarget && setShowUpload(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              transition={{ duration: 0.15 }}
              className="bg-[#0D1220] border border-white/8 rounded-2xl p-6 w-[420px] shadow-2xl"
            >
              <div className="flex items-center justify-between mb-5">
                <div>
                  <h2 className="text-white font-semibold">Upload Repository</h2>
                  <p className="text-gray-500 text-xs mt-0.5">ZIP file or GitHub URL</p>
                </div>
                <button onClick={() => setShowUpload(false)} className="text-gray-600 hover:text-gray-400 text-lg">✕</button>
              </div>

              {/* Drag & Drop Zone */}
              <div
                onDrop={handleDrop}
                onDragOver={e => { e.preventDefault(); setDragActive(true); }}
                onDragLeave={() => setDragActive(false)}
                className={`border-2 border-dashed rounded-xl p-8 text-center transition-all ${
                  dragActive ? "border-violet-500 bg-violet-500/5" : "border-white/10 hover:border-white/20"
                }`}
              >
                <div className="text-3xl mb-2">📦</div>
                <p className="text-gray-400 text-sm font-medium">Drop your ZIP here</p>
                <p className="text-gray-600 text-xs mt-1 mb-3">or browse files</p>
                <label className="cursor-pointer bg-white/6 hover:bg-white/10 border border-white/8 rounded-lg px-4 py-2 text-xs text-gray-300 transition-all">
                  Browse ZIP
                  <input
                    type="file"
                    accept=".zip"
                    className="hidden"
                    onChange={e => handleZipUpload(e.target.files[0])}
                  />
                </label>
              </div>

              {/* Divider */}
              <div className="flex items-center gap-3 my-4">
                <div className="flex-1 h-px bg-white/6" />
                <span className="text-gray-600 text-xs">or</span>
                <div className="flex-1 h-px bg-white/6" />
              </div>

              {/* GitHub */}
              <div className="space-y-2">
                <input
                  type="text"
                  placeholder="https://github.com/user/repo"
                  value={repoUrl}
                  onChange={e => setRepoUrl(e.target.value)}
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

              {/* Status */}
              {uploadStatus && (
                <div className={`mt-4 flex items-center gap-2 px-4 py-3 rounded-xl text-xs border ${
                  uploadSuccess
                    ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                    : uploading
                    ? "bg-blue-500/10 border-blue-500/20 text-blue-400"
                    : "bg-red-500/10 border-red-500/20 text-red-400"
                }`}>
                  <span>{uploading ? "⏳" : uploadSuccess ? "✅" : "❌"}</span>
                  <span>{uploadStatus}</span>
                </div>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}