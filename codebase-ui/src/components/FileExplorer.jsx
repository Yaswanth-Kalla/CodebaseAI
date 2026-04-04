import { useEffect, useState } from "react";

const getFileName = (path) => path.replace(/\\/g, "/").split("/").pop();

const getFileIcon = (name) => {
  const ext = name.split(".").pop().toLowerCase();
  const map = {
    js: "🟨", jsx: "⚛️", ts: "🔷", tsx: "⚛️",
    py: "🐍", go: "🐹", rs: "🦀", java: "☕",
    css: "🎨", html: "🌐", json: "📋", md: "📝",
    yaml: "⚙️", yml: "⚙️", env: "🔐", sh: "🐚",
    txt: "📄", sql: "🗄️",
  };
  return map[ext] || "📄";
};

export default function FileExplorer({ fileToOpen }) {
  const [files, setFiles] = useState([]);
  const [content, setContent] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [highlightLine, setHighlightLine] = useState(null);
  const [loadingFiles, setLoadingFiles] = useState(true);
  const [loadingContent, setLoadingContent] = useState(false);
  const [search, setSearch] = useState("");

  useEffect(() => {
    setLoadingFiles(true);
    fetch("https://codebaseai-1.onrender.com/files")
      .then(res => res.json())
      .then(data => {
        const paths = [...new Set(data.files.map(f => f.path))];
        setFiles(paths);
      })
      .catch(err => console.error("File fetch error:", err))
      .finally(() => setLoadingFiles(false));
  }, []);

  const openFile = async (file) => {
    setSelectedFile(file);
    setLoadingContent(true);
    setContent("");
    setHighlightLine(null);
    try {
      const res = await fetch(`https://codebaseai-1.onrender.com/file-content?path=${encodeURIComponent(file)}`);
      const data = await res.json();
      setContent(data.content || "");
    } catch (err) {
      console.error("File load error:", err);
      setContent("// Error loading file");
    }
    setLoadingContent(false);
  };

  useEffect(() => {
    if (!fileToOpen?.file) return;
    openFile(fileToOpen.file);
  }, [fileToOpen]);

  useEffect(() => {
    if (!fileToOpen || !content) return;
    highlightFunction(fileToOpen.functionName, content);
  }, [content]);

  const highlightFunction = (functionName, fileContent) => {
    if (!functionName) return;
    const lines = fileContent.split("\n");
    const regex = new RegExp(`\\b(def|async\\s+def|function)\\s+${functionName.trim()}\\b`, "i");
    const index = lines.findIndex(line => regex.test(line));
    if (index !== -1) {
      setHighlightLine(index);
      setTimeout(() => {
        document.getElementById(`line-${index}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
      }, 200);
    }
  };

  const filteredFiles = search.trim()
    ? files.filter(f => getFileName(f).toLowerCase().includes(search.toLowerCase()))
    : files;

  const lines = content.split("\n");

  return (
    <div className="flex h-full bg-[#070B14]">

      {/* FILE LIST */}
      <div className="w-64 border-r border-white/5 flex flex-col shrink-0">
        <div className="p-3 border-b border-white/5">
          <div className="flex items-center gap-2 bg-white/4 border border-white/8 rounded-lg px-3 py-1.5 focus-within:border-violet-500/40 transition-colors">
            <span className="text-gray-600 text-xs">🔍</span>
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search files..."
              className="bg-transparent outline-none text-xs text-white placeholder-gray-600 w-full"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-2">
          {loadingFiles ? (
            <div className="flex flex-col gap-1.5 p-2">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="h-7 bg-white/4 rounded animate-pulse" />
              ))}
            </div>
          ) : filteredFiles.length === 0 ? (
            <p className="text-gray-600 text-xs px-3 py-4 text-center">
              {search ? "No files match" : "No files loaded — upload a repo first"}
            </p>
          ) : (
            filteredFiles.map((file, i) => {
              const name = getFileName(file);
              return (
                <button
                  key={i}
                  onClick={() => openFile(file)}
                  className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-left transition-all truncate
                    ${selectedFile === file
                      ? "bg-violet-600/20 text-violet-300 border border-violet-500/20"
                      : "text-gray-400 hover:text-gray-200 hover:bg-white/4"
                    }`}
                >
                  <span className="shrink-0">{getFileIcon(name)}</span>
                  <span className="truncate">{name}</span>
                </button>
              );
            })
          )}
        </div>

        <div className="px-3 py-2 border-t border-white/5">
          <p className="text-[10px] text-gray-600">{files.length} files indexed</p>
        </div>
      </div>

      {/* FILE CONTENT */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {!selectedFile ? (
          <div className="flex-1 flex flex-col items-center justify-center text-center gap-3">
            <span className="text-4xl">📂</span>
            <p className="text-gray-500 text-sm">Select a file to view its contents</p>
          </div>
        ) : (
          <>
            {/* File header */}
            <div className="h-10 border-b border-white/5 flex items-center px-4 gap-3 shrink-0">
              <span className="text-sm">{getFileIcon(getFileName(selectedFile))}</span>
              <span className="text-gray-400 text-xs font-mono truncate">{selectedFile}</span>
              {!loadingContent && (
                <span className="ml-auto text-[10px] text-gray-600">{lines.length} lines</span>
              )}
            </div>

            {/* Code */}
            {loadingContent ? (
              <div className="flex-1 flex items-center justify-center">
                <div className="flex gap-1.5">
                  {[0, 1, 2].map(n => (
                    <span key={n} className="w-2 h-2 rounded-full bg-violet-500 animate-bounce" style={{ animationDelay: `${n * 0.15}s` }} />
                  ))}
                </div>
              </div>
            ) : (
              <div className="flex-1 overflow-auto">
                <table className="w-full border-collapse text-xs font-mono">
                  <tbody>
                    {lines.map((line, i) => (
                      <tr
                        key={i}
                        id={`line-${i}`}
                        className={`group transition-colors ${
                          i === highlightLine
                            ? "bg-yellow-400/15 border-l-2 border-yellow-400"
                            : "hover:bg-white/2"
                        }`}
                      >
                        <td className="select-none text-right text-gray-700 pr-4 pl-4 py-0.5 w-12 border-r border-white/4 group-hover:text-gray-500">
                          {i + 1}
                        </td>
                        <td className={`pl-4 pr-4 py-0.5 whitespace-pre ${
                          i === highlightLine ? "text-yellow-200" : "text-gray-300"
                        }`}>
                          {line || " "}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
