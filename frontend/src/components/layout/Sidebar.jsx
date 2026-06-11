import { useFileUpload } from "../../hooks/useFileUpload";
import UploadZone from "../upload/UploadZone";
import FileList from "../upload/FileList";

export default function Sidebar() {
  const { files, addFiles, removeFile } = useFileUpload();

  return (
    <div className="flex flex-col h-full p-4 gap-4 text-white">
      <div className="text-2xl font-bold mb-6 border-b border-gray-700 pb-4">
        MultiModal RAG
      </div>

      <div>
        <p className="text-xs uppercase tracking-widest text-gray-500 mb-3">Upload Documents</p>
        <UploadZone onDrop={addFiles} />
        <FileList files={files} onRemove={removeFile} />
      </div>

      <div className="mt-auto">
        <p className="text-xs uppercase tracking-widest text-gray-500 mb-2">Chat History</p>
        <div className="text-gray-400 text-sm p-3 bg-gray-900 rounded">No previous chats</div>
      </div>
    </div>
  );
}