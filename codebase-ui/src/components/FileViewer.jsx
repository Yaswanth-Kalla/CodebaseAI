import { useEffect, useState } from "react";

export default function FileViewer({ filePath }) {
  const [content, setContent] = useState("");

  useEffect(() => {
    if (!filePath) return;

    fetch(`https://codebaseai-1.onrender.com/file-content?path=${filePath}`)
      .then(res => res.json())
      .then(data => setContent(data.content));
  }, [filePath]);

  return (
    <div className="h-full bg-black text-green-400 p-4 overflow-auto">
      <pre className="text-sm whitespace-pre-wrap">{content}</pre>
    </div>
  );
}
