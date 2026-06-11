import { CheckCircle, XCircle, Loader2, X } from "lucide-react";

export default function FileList({ files, onRemove }) {
  if (!files.length) return null;

  return (
    <div className="mt-4 space-y-2">
      {files.map((file) => (
        <div key={file.id} className="bg-gray-900 rounded-lg p-3 flex items-center gap-3">
          {file.status === "uploading" && <Loader2 className="w-5 h-5 animate-spin text-blue-500" />}
          {file.status === "done" && <CheckCircle className="w-5 h-5 text-green-500" />}
          {file.status === "error" && <XCircle className="w-5 h-5 text-red-500" />}

          <div className="flex-1 min-w-0">
            <p className="text-sm truncate">{file.name}</p>
            {file.progress > 0 && (
              <div className="h-1 bg-gray-800 rounded mt-1.5">
                <div className="h-1 bg-blue-500 rounded" style={{ width: `${file.progress}%` }} />
              </div>
            )}
          </div>

          <button onClick={() => onRemove(file.id)} className="text-gray-500 hover:text-red-400">
            <X className="w-4 h-4" />
          </button>
        </div>
      ))}
    </div>
  );
}