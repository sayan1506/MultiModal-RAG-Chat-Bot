import { useState } from "react";
import { uploadFile } from "../services/api";

export function useFileUpload() {
  const [files, setFiles] = useState([]);

  const addFiles = async (acceptedFiles) => {
    const newFiles = acceptedFiles.map((file) => ({
      id: crypto.randomUUID(),
      name: file.name,
      status: "uploading",
      progress: 0,
    }));

    setFiles((prev) => [...prev, ...newFiles]);

    for (let i = 0; i < acceptedFiles.length; i++) {
      const file = acceptedFiles[i];
      const fileEntry = newFiles[i];

      try {
        await uploadFile(file, (progress) => {
          setFiles((prev) =>
            prev.map((f) =>
              f.id === fileEntry.id ? { ...f, progress } : f
            )
          );
        });
        setFiles((prev) =>
          prev.map((f) =>
            f.id === fileEntry.id ? { ...f, status: "done", progress: 100 } : f
          )
        );
      } catch (err) {
        console.error(err);
        setFiles((prev) =>
          prev.map((f) =>
            f.id === fileEntry.id ? { ...f, status: "error" } : f
          )
        );
      }
    }
  };

  const removeFile = (id) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  };

  return { files, addFiles, removeFile };
}