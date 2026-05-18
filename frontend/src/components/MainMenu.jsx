// src/components/MainMenu.jsx
import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import axios from "axios";

export default function MainMenu({ onStartGame, onOpenAbout }) {
  const options = ["Continue", "New Save", "Load Save", "About"];
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [mode, setMode] = useState("menu");
  const [saveName, setSaveName] = useState("");
  const [creating, setCreating] = useState(false);
  const [saves, setSaves] = useState([]);
  const [selectedIndex, setSelectedIndex] = useState(null);
  // confirmDelete now stores only id + name (prevents [object Object] issue)
  const [confirmDelete, setConfirmDelete] = useState({ show: false, id: null, name: null });
  const [showSplash, setShowSplash] = useState(true);

  useEffect(() => {
    const handleMouseMove = (e) => {
      const x = (e.clientX / window.innerWidth - 0.5) * 25;
      const y = (e.clientY / window.innerHeight - 0.5) * 25;
      setOffset({ x, y });
    };
    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, []);

  useEffect(() => {
    const t = setTimeout(() => setShowSplash(false), 4500);
    return () => clearTimeout(t);
  }, []);

  useEffect(() => {
    const handleKey = (e) => {
      if (e.key === "Escape") setMode("menu");
      if (e.key === "Enter" && mode === "new") handleCreateSave();
      if (e.key === "Enter" && confirmDelete.show) handleDeleteSaveConfirmed();
      if (e.key === "Delete" && mode === "load" && selectedIndex !== null) {
        const s = saves[selectedIndex];
        if (s) handleDeleteSaveRequest(s);
      }
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [mode, selectedIndex, saves, confirmDelete, saveName]);

  async function loadSaves() {
  try {
    const res = await axios.get("/api/saves");
    let data = res.data.saves || [];

    // Normalize entries to objects with id/name/created_at
    const normalized = data.map((s) => {
      if (s && typeof s === "object") {
        return {
          id: String(s.id ?? s.name ?? ""),
          name: String(s.name ?? s.id ?? ""),
          created_at: Number(s.created_at || 0),
        };
      } else {
        const id = String(s);
        return { id, name: id, created_at: 0 };
      }
    });

    // Sort by created_at ascending (oldest first)
    normalized.sort((a, b) => (a.created_at || 0) - (b.created_at || 0));

    setSaves(normalized);
    setSelectedIndex(null);
  } catch (err) {
    console.error("loadSaves error:", err);
    setSaves([]);
  }
}



  async function handleContinue() {
  try {
    const last = localStorage.getItem("active_save");
    if (last) return onStartGame(last, { created: false });

    const res = await axios.get("/api/saves");
    const list = res.data.saves || [];
    if (list.length === 0) return alert("No saves found.");
    const latest = list[list.length - 1].id || list[list.length - 1].name;
    localStorage.setItem("active_save", latest);
    onStartGame(latest, { created: false });
  } catch (err) {
    console.error("continue error:", err);
    alert("Failed to load saves.");
  }
}


  async function handleCreateSave() {
  if (!saveName || !saveName.trim()) return alert("Enter a name.");
  try {
    setCreating(true);
    const res = await axios.post("/api/save/new", { name: saveName });
    setCreating(false);
    if (res.data?.status !== "ok") {
      alert(res.data?.message || "Failed to create save.");
      return;
    }
    const id = res.data.save;

    // remove any previous stored player name for this save id
    try {
      localStorage.removeItem(`save_${id}_player`);
    } catch (e) {
      console.warn("Failed to remove previous localStorage player name:", e);
    }

    // activate and go to hub
    localStorage.setItem("active_save", id);
    // PASS opts.created = true so Hub knows this is a freshly created save
    onStartGame(id, { created: true });
  } catch (err) {
    setCreating(false);
    console.error("Create save error:", err);
    alert("Error creating save.");
  }
}



  function handleLoad(save) {
  console.log("handleLoad called with:", save);
  const id =
    save && typeof save === "object"
      ? save.id || save.name || null
      : typeof save === "string"
      ? save
      : null;

  if (!id) {
    if (typeof save === "string") {
      try {
        const parsed = JSON.parse(save);
        if (parsed && parsed.id) {
          localStorage.setItem("active_save", String(parsed.id));
          onStartGame(String(parsed.id), { created: false });
          return;
        }
      } catch (e) {
        // ignore parse error
      }
    }
    console.error("handleLoad: invalid save value:", save);
    alert("Invalid save selected.");
    return;
  }

  const idStr = String(id);
  localStorage.setItem("active_save", idStr);
  onStartGame(idStr, { created: false });
}



  // store only id + name in confirmDelete to avoid sending objects in URL
  function handleDeleteSaveRequest(save) {
  // normalize incoming save to { id, name }
  const id = save && typeof save === "object" ? (save.id ?? save.name ?? null) : (typeof save === "string" ? save : null);
  const name = (save && typeof save === "object" ? (save.name ?? id) : id) ?? "unknown";
  if (!id) {
    alert("Invalid save.");
    console.error("handleDeleteSaveRequest: invalid save value:", save);
    return;
  }
  // store only id + name to avoid passing objects to URL
  setConfirmDelete({ show: true, save: { id: String(id), name: String(name) } });
}

  async function handleDeleteSaveConfirmed() {
  try {
    const raw = confirmDelete.save;
    const id =
      raw && typeof raw === "object"
        ? raw.id
        : typeof raw === "string"
        ? raw
        : null;

    if (!id) {
      console.error("Invalid save id.");
      setConfirmDelete({ show: false, save: null });
      return;
    }

    console.log("Deleting save id:", id);

    const encoded = encodeURIComponent(String(id));
    const res = await fetch(`/api/save/${encoded}`, { method: "DELETE" });

    const text = await res.text().catch(() => "");
    let body = null;
    try {
      body = text ? JSON.parse(text) : null;
    } catch (e) {
      body = null;
    }

    console.log("Delete response status:", res.status, "body:", body || text);

    if (res.ok && (!body || body.status === "ok")) {
      await loadSaves();

      try {
        localStorage.removeItem(`save_${id}_player`);
      } catch (e) {
        console.warn("Failed cleaning localStorage for deleted save:", e);
      }

      setConfirmDelete({ show: false, save: null });
      setSelectedIndex(null);
      if (localStorage.getItem("active_save") === String(id)) {
        localStorage.removeItem("active_save");
      }
      // no alert here
      return;
    }

    console.error("Failed to delete save. Check console for details.");
    setConfirmDelete({ show: false, save: null });
  } catch (err) {
    console.error("Delete error:", err);
    setConfirmDelete({ show: false, save: null });
  }
}


  return (
    <div className="relative w-full h-screen overflow-hidden bg-black font-serif tracking-wide">
      <AnimatePresence>
        {showSplash && (
          <motion.div
            key="splash"
            className="absolute inset-0 z-60 flex items-center justify-center bg-black"
            initial={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.6 }}
          >
            <motion.img
              src="/splash-logo.png"
              alt="Flash Study AI"
              className="absolute inset-0 w-full h-full object-cover"
              initial={{ scale: 1.05, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ duration: 1.6 }}
            />
          </motion.div>
        )}
      </AnimatePresence>

      <motion.div
        className="absolute inset-0 bg-cover bg-center"
        style={{
          backgroundImage: "url('/menu-bg.jpg')",
          transform: `translate(${offset.x}px, ${offset.y}px) scale(1.05)`,
        }}
      />

      <div className="absolute left-0 top-0 h-full w-[45%] bg-gradient-to-r from-black via-black/90 to-transparent z-10" />

      <motion.div
        className="absolute top-[18%] left-10 text-white z-30"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.8 }}
      >
        <h1 className="text-5xl font-extrabold">Flash Study</h1>
        <h2 className="text-5xl text-blue-400 mt-1 tracking-[0.3em]">AI</h2>
      </motion.div>

      <AnimatePresence mode="wait">
        {mode === "menu" && (
          <motion.div
            key="menu"
            className="absolute left-12 top-[42%] z-30 space-y-3"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            {options.map((opt, i) => (
              <motion.div
                key={opt}
                className="group cursor-pointer select-none"
                initial={{ opacity: 0, x: -40 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.18 + 0.6 }}
                onClick={() => {
                  if (opt === "Continue") return handleContinue();
                  if (opt === "New Save") return setMode("new");
                  if (opt === "Load Save") {
                    setMode("load");
                    loadSaves();
                    return;
                  }
                  if (opt === "About") return onOpenAbout();
                }}
              >
                <span className="text-2xl text-gray-300 group-hover:text-blue-400 transition">
                  {opt}
                </span>
                <div className="w-0 group-hover:w-24 h-[2px] bg-blue-400 transition-all"></div>
              </motion.div>
            ))}
          </motion.div>
        )}

        {mode === "new" && (
          <motion.div
            key="new"
            className="absolute left-12 top-[45%] z-30"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <h3 className="text-xl text-gray-300 mb-4">Create New Save</h3>
            <input
              className="bg-transparent border-b border-blue-400 text-white text-lg mb-4"
              placeholder="Enter save name..."
              value={saveName}
              onChange={(e) => setSaveName(e.target.value)}
            />
            <div className="mt-6 space-x-4">
              <button
                onClick={handleCreateSave}
                disabled={creating}
                className="px-6 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-md"
              >
                {creating ? "Saving..." : "Save"}
              </button>
              <button
                onClick={() => setMode("menu")}
                className="px-6 py-2 bg-gray-600 hover:bg-gray-500 text-white rounded-md"
              >
                Cancel
              </button>
            </div>
          </motion.div>
        )}

        {mode === "load" && (
          <motion.div
            key="load"
            className="absolute left-12 top-[40%] z-30"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <h3 className="text-xl text-gray-300 mb-4">Load Existing Save</h3>
            {saves.length > 0 ? (
              <ul className="space-y-3">
                {saves.map((save, i) => {
                  const label = save.name || save.id || String(save);
                  return (
                    <li
                      key={save.id || label + i}
                      className={`flex justify-between cursor-pointer ${
                        selectedIndex === i ? "text-blue-400" : "text-gray-300 hover:text-blue-400"
                      }`}
                      onClick={() => setSelectedIndex(i)}
                    >
                      <span onDoubleClick={() => handleLoad(save)}>
                        {i + 1}. {label}
                      </span>

                      <button
                        onClick={(e) => { e.stopPropagation(); handleDeleteSaveRequest(save); }}
                        className="px-3 py-1 text-sm bg-red-700 hover:bg-red-600 text-white rounded"
                      >
                        Delete
                      </button>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="text-gray-500">No saves found.</p>
            )}

            <button
              onClick={() => setMode("menu")}
              className="mt-6 px-6 py-2 bg-gray-600 hover:bg-gray-500 text-white rounded-md"
            >
              Back
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {confirmDelete.show && (
          <motion.div
            className="absolute inset-0 bg-black/80 flex items-center justify-center z-40"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <motion.div
              className="bg-black/90 border border-gray-700 p-10 rounded-2xl text-center w-[480px]"
              initial={{ scale: 0.9 }}
              animate={{ scale: 1 }}
            >
              <p className="text-2xl text-gray-100 mb-10">
                Delete Save: <span className="text-blue-400">{confirmDelete.name || "?"}</span>
              </p>
              <div className="flex justify-center gap-16">
                <button
                  onClick={handleDeleteSaveConfirmed}
                  className="px-10 py-3 text-lg bg-blue-600 hover:bg-blue-500 text-white rounded-md"
                >
                  YES
                </button>
                <button
                  onClick={() => setConfirmDelete({ show: false, id: null, name: null })}
                  className="px-10 py-3 text-lg bg-red-600 hover:bg-red-500 text-white rounded-md"
                >
                  NO
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
