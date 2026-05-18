import React, { useState } from "react";

export default function UploadPDF({ saveName, onUploaded }) {
  const [loading, setLoading] = useState(false);

  const handleFile = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setLoading(true);

    const fd = new FormData();
    fd.append("file", f);

    try {
      const res = await fetch(`/api/upload?save_id=${encodeURIComponent(saveName)}`, {
        method: "POST",
        body: fd,
      });
      const data = await res.json();
      setLoading(false);

      if (!res.ok) {
        alert("Upload failed: " + (data.error || data.message || "Server error"));
        return;
      }

      // Notify parent / refresh list
      onUploaded && onUploaded(data.upload || { id: data.pdf_id, filename: data.filename });
    } catch (err) {
      console.error("Upload error:", err);
      setLoading(false);
      alert("Upload failed.");
    } finally {
      e.target.value = "";
    }
  };

  // optional helper: delete an uploaded file (scoped to save)
  const handleDelete = async (uploadId) => {
    if (!confirm("Delete this file?")) return;
    try {
      const res = await fetch(
        `/api/upload/${uploadId}?save_id=${encodeURIComponent(saveName)}`,
        { method: "DELETE" }
      );
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        alert("Delete failed: " + (j.message || "Server error"));
      } else {
        onUploaded && onUploaded(null); // signal parent to refresh
      }
    } catch (err) {
      console.error("Delete error:", err);
      alert("Delete failed.");
    }
  };

  return (
    <div>
      <label className="px-3 py-2 bg-blue-600 rounded-md cursor-pointer">
        Upload PDF
        <input type="file" accept="application/pdf" onChange={handleFile} className="sr-only" />
      </label>

      {loading && <div className="text-sm text-gray-400 mt-2">Uploading...</div>}

      {/* If you want a small UI for deletion inside this component, you can use handleDelete(uploadId) */}
    </div>
  );
}
