import { useDropzone } from "react-dropzone";
import { UploadCloud } from "lucide-react";

export default function UploadZone({ onDrop }) {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.presentationml.presentation": [".pptx"],
    },
    maxSize: 50 * 1024 * 1024, // 50MB
  });

  return (
    <div
      {...getRootProps()}
      className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all
        ${isDragActive ? "border-blue-500 bg-blue-500/10" : "border-gray-700 hover:border-gray-500"}`}
    >
      <input {...getInputProps()} />
      <UploadCloud className="w-12 h-12 mx-auto mb-4 text-gray-400" />
      <p className="text-lg font-medium">
        {isDragActive ? "Drop files here" : "Drag & drop PDF or PPTX"}
      </p>
      <p className="text-sm text-gray-500 mt-1">or click to browse</p>
      <p className="text-xs text-gray-600 mt-2">Max 50 MB</p>
    </div>
  );
}