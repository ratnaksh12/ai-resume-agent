import React, { useState } from "react";

export default function UploadResume({ apiBase, onUploaded }) {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("Idle");

  const handleUpload = async () => {
    if (!file) {
      alert("Please choose a file first.");
      return;
    }

    setStatus("Uploading...");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${apiBase}/upload_resume`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        throw new Error(`Upload failed: ${res.status}`);
      }

      const data = await res.json();
      setStatus("Uploaded!");

      if (onUploaded) {
        onUploaded(data.resume_id, data.version_id);
      }
    } catch (err) {
      console.error(err);
      setStatus("Error");
      alert("Failed to upload resume.");
    }
  };

  return (
    <div className="bg-white p-6 rounded-xl shadow">
      <h2 className="font-semibold text-xl mb-4">Upload Resume</h2>
      <input
        type="file"
        className="mb-3 block w-full text-sm"
        onChange={(e) => setFile(e.target.files?.[0] || null)}
      />
      <button
        onClick={handleUpload}
        className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium"
      >
        Upload
      </button>
      <div className="mt-2 text-xs text-gray-500">{status}</div>
    </div>
  );
}
