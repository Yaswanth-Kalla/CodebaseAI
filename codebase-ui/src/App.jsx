import { useState } from "react";
import Chat from "./components/Chat";
import FileExplorer from "./components/FileExplorer";
import GraphView from "./components/GraphView";

export default function App() {
  const [activeTab, setActiveTab] = useState("chat");
  const [history, setHistory] = useState([]);
  const [chatStore, setChatStore] = useState({});
  const [selectedQuery, setSelectedQuery] = useState(null);
  const [fileToOpen, setFileToOpen] = useState(null);

  const handleFileOpenFromChat = (fileData) => {
    setFileToOpen(fileData);
    setActiveTab("files");
  };

  const tabs = [
    { id: "chat", icon: "💬", label: "Chat" },
    { id: "files", icon: "📂", label: "Explorer" },
    // { id: "graph", icon: "🕸️", label: "Graph" },
  ];

  return (
    <div className="w-screen h-screen bg-[#070B14] text-white flex overflow-hidden font-sans">

      {/* SIDEBAR */}
      <aside className="fixed left-0 top-0 h-screen w-60 flex flex-col border-r border-white/5 bg-[#070B14] z-20">

        {/* Logo */}
        <div className="px-5 py-5 border-b border-white/5">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-violet-500 to-blue-500 flex items-center justify-center text-xs">⬡</div>
            <div>
              <p className="text-white text-sm font-semibold leading-tight">CodebaseAI</p>
              <p className="text-gray-500 text-[10px]">RAG-powered explorer</p>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="px-3 py-4 space-y-0.5">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-150 text-left
                ${activeTab === tab.id
                  ? "bg-white/8 text-white"
                  : "text-gray-500 hover:text-gray-300 hover:bg-white/4"
                }`}
            >
              <span className="text-base">{tab.icon}</span>
              <span className="font-medium">{tab.label}</span>
              {activeTab === tab.id && (
                <span className="ml-auto w-1 h-4 rounded-full bg-violet-500" />
              )}
            </button>
          ))}
        </nav>

        {/* History */}
        <div className="flex-1 overflow-y-auto px-3 py-2 border-t border-white/5 mt-2">
          <p className="text-[10px] uppercase tracking-widest text-gray-600 px-3 mb-2 pt-2">History</p>
          {history.length === 0 && (
            <p className="text-gray-600 text-xs px-3 py-1">No queries yet</p>
          )}
          {history.map((h, i) => (
            <button
              key={i}
              onClick={() => { setActiveTab("chat"); setSelectedQuery(h); }}
              className="w-full text-left text-xs text-gray-500 hover:text-gray-300 px-3 py-1.5 rounded hover:bg-white/4 truncate transition-colors"
            >
              <span className="text-gray-600 mr-1.5">›</span>{h}
            </button>
          ))}
        </div>

        {/* Footer */}
        <div className="px-5 py-4 border-t border-white/5">
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-[10px] text-gray-500">Backend connected</span>
          </div>
        </div>
      </aside>

      {/* MAIN */}
      <main className="ml-60 flex-1 h-screen overflow-hidden">
        {activeTab === "chat" && (
          <Chat
            setHistory={setHistory}
            chatStore={chatStore}
            setChatStore={setChatStore}
            selectedQuery={selectedQuery}
            setFileToOpen={handleFileOpenFromChat}
          />
        )}
        {activeTab === "files" && <FileExplorer fileToOpen={fileToOpen} />}
        {/* {activeTab === "graph" && <GraphView />} */}
      </main>
    </div>
  );
}