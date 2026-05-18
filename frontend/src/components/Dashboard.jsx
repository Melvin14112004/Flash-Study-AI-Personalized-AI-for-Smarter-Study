import React, { useEffect, useState, useCallback, useRef } from "react";

export default function Dashboard({
  saveName,
  onBack,
  onAddUpload,
  onSelectUpload,
  onRemoveUpload,
}) {
  const [uploads, setUploads] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const pollingRef = useRef({});
  const [confirmDelete, setConfirmDelete] = useState({
    show: false,
    id: null,
    name: null,
  });

  const prettySaveName = (name) => {
    if (!name) return "";
    const spaced = String(name).replace(/_/g, " ").replace(/\s+/g, " ").trim();
    return spaced
      .split(" ")
      .map((w) => (w ? w.charAt(0).toUpperCase() + w.slice(1) : ""))
      .join(" ");
  };

  const displayNameNoExt = (filename) => {
    if (!filename) return "";
    const base = String(filename).split(/[\\/]/).pop();
    return base.replace(/\.[^/.]+$/, "");
  };

  const fetchUploads = async () => {
    if (!saveName) return [];
    try {
      const res = await fetch(
        `/api/uploads?save_id=${encodeURIComponent(saveName)}`
      );
      const data = await res.json();
      const list = data.uploads || [];
      setUploads(list);

      if (!selectedId && list.length > 0) {
        setSelectedId(list[list.length - 1].id);
      }

      if (typeof onAddUpload === "function") {
        try {
          onAddUpload(null, list);
        } catch (e) {
          console.warn("onAddUpload failed:", e);
        }
      }
      return list;
    } catch (err) {
      console.error("Failed to fetch uploads", err);
      return [];
    }
  };

  useEffect(() => {
    fetchUploads();
    const t = setInterval(fetchUploads, 6000);
    return () => clearInterval(t);
  }, [saveName]);

  const escHandler = useCallback(
    (e) => {
      if (e.key === "Escape") onBack && onBack();
    },
    [onBack]
  );

  useEffect(() => {
    window.addEventListener("keydown", escHandler);
    return () => window.removeEventListener("keydown", escHandler);
  }, [escHandler]);

  const pollForSummary = async (uploadId) => {
    if (!uploadId) return;
    if (pollingRef.current[uploadId]) return;
    pollingRef.current[uploadId] = true;

    const start = Date.now();
    while (Date.now() - start < 30000) {
      const list = await fetchUploads();
      const u = list.find((x) => x.id === uploadId);
      if (u && u.summary && u.summary.trim().length > 5) {
        pollingRef.current[uploadId] = false;
        return true;
      }
      await new Promise((r) => setTimeout(r, 2000));
    }

    pollingRef.current[uploadId] = false;
    return false;
  };

  const handleFileChange = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;

    const form = new FormData();
    form.append("file", f);

    try {
      const res = await fetch(
        `/api/upload?save_id=${encodeURIComponent(saveName)}`,
        {
          method: "POST",
          body: form,
        }
      );

      const data = await res.json();

      if (!res.ok) {
        console.warn(
          "Upload failed:",
          data.error || data.message || "Server error"
        );
        return;
      }

      const uploaded =
        data.upload || { id: data.pdf_id, filename: data.filename };

      await fetchUploads();

      if (uploaded?.id) {
        setSelectedId(uploaded.id);
        await pollForSummary(uploaded.id);
        await fetchUploads();
      }
    } catch (err) {
      console.error("Upload error:", err);
    }

    e.target.value = "";
  };

  const handleDelete = async (id) => {
    if (!id) return;
    try {
      await fetch(
        `/api/upload/${encodeURIComponent(
          id
        )}?save_id=${encodeURIComponent(saveName)}`,
        { method: "DELETE" }
      );

      const list = await fetchUploads();
      if (selectedId === id) setSelectedId(null);

      if (typeof onRemoveUpload === "function") {
        try {
          onRemoveUpload(id);
        } catch (e) {
          console.warn("onRemoveUpload failed:", e);
        }
      }
      if (typeof onAddUpload === "function") {
        try {
          onAddUpload(null, list);
        } catch (e) {
          console.warn("onAddUpload failed:", e);
        }
      }
    } catch (err) {
      console.error("Delete failed:", err);
    } finally {
      setConfirmDelete({ show: false, id: null, name: null });
    }
  };

  return (
    <div className="w-full min-h-screen p-8">
      {/* Container width set to 80% */}
      <div className="w-[80%] mx-auto">
        <div className="bg-[#070607] p-6 rounded-md border border-blue-900/30">
          {/* HEADER SECTION */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
            <div>
              <h2 className="text-2xl text-blue-200">
                Dashboard {prettySaveName(saveName)}
              </h2>
              <p className="text-sm text-gray-500 mt-1">Manage your files</p>
            </div>

            <div className="flex gap-3">
              <button
                onClick={onBack}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-md text-sm transition-colors"
              >
                Back to Hub
              </button>

              <label className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-md cursor-pointer text-sm transition-colors flex items-center gap-2">
                <span>Upload PDF</span>
                <input
                  onChange={handleFileChange}
                  accept="application/pdf"
                  type="file"
                  className="sr-only"
                />
              </label>
            </div>
          </div>

          {/* UPLOADS LIST SECTION */}
          {uploads.length === 0 ? (
            <div className="text-gray-400 py-8 text-center border border-dashed border-gray-800 rounded-md">
              No uploads yet. Click "Upload PDF" to start.
            </div>
          ) : (
            <ul className="space-y-3">
              {uploads.map((u) => (
                <li
                  key={u.id}
                  className={`flex items-center justify-between p-3 rounded-md border border-transparent ${
                    selectedId === u.id
                      ? "bg-blue-900/30 border-blue-800/50"
                      : "bg-[#020203] hover:border-blue-900/30"
                  }`}
                >
                  <div
                    className="flex-1 cursor-pointer"
                    onClick={() => {
                      setSelectedId(u.id);
                      if (typeof onSelectUpload === "function") {
                        onSelectUpload(u.id);
                      }
                    }}
                  >
                    <div className="font-medium text-white">
                      {displayNameNoExt(u.name)}
                    </div>
                    <div className="text-xs text-gray-400">
                      {u.createdAt
                        ? new Date(u.createdAt).toLocaleString()
                        : u.created_at
                        ? new Date(u.created_at).toLocaleString()
                        : ""}
                    </div>
                  </div>

                  <button
                    onClick={() =>
                      setConfirmDelete({
                        show: true,
                        id: u.id,
                        name: displayNameNoExt(u.name),
                      })
                    }
                    className="ml-4 px-3 py-1 bg-red-600 hover:bg-red-700 text-white rounded text-xs transition-colors"
                  >
                    Delete
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* CONFIRM DELETE MODAL */}
      {confirmDelete.show && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
          <div className="bg-black/90 border border-gray-700 p-10 rounded-2xl text-center w-[480px]">
            <p className="text-2xl text-gray-100 mb-10">
              Delete Upload:{" "}
              <span className="text-blue-400">
                {confirmDelete.name || "?"}
              </span>
            </p>
            <div className="flex justify-center gap-16">
              <button
                onClick={() => {
                  handleDelete(confirmDelete.id);
                }}
                className="px-10 py-3 text-lg bg-blue-600 hover:bg-blue-500 text-white rounded-md"
              >
                YES
              </button>
              <button
                onClick={() =>
                  setConfirmDelete({ show: false, id: null, name: null })
                }
                className="px-10 py-3 text-lg bg-red-600 hover:bg-red-500 text-white rounded-md"
              >
                NO
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}