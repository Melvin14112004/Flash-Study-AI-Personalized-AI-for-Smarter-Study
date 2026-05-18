// src/components/NameModal.jsx
import React, { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";

export default function NameModal({
  open,
  initial = "",
  prompt = "Hey! What should I call you?",
  onConfirm,
  onCancel,
}) {
  const [name, setName] = useState(initial || "");
  const inputRef = useRef(null);

  useEffect(() => {
    setName(initial || "");
    if (open) {
      const t = setTimeout(() => inputRef.current?.focus(), 80);
      return () => clearTimeout(t);
    }
  }, [open, initial]);

  useEffect(() => {
    const handler = (e) => {
      if (!open) return;
      if (e.key === "Enter") {
        onConfirm && onConfirm((name || "").trim() || "Friend");
      } else if (e.key === "Escape") {
        onCancel && onCancel();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, name, onConfirm, onCancel]);

  if (!open) return null;

  return (
    <motion.div
      className="fixed inset-0 z-60 flex items-center justify-center bg-black/70"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      <motion.div
        className="w-[520px] max-w-[92%] rounded-2xl p-8"
        initial={{ y: 20, scale: 0.98, opacity: 0 }}
        animate={{ y: 0, scale: 1, opacity: 1 }}
        transition={{ type: "spring", stiffness: 200, damping: 18 }}
        style={{
          background:
            "linear-gradient(180deg, rgba(6,8,15,0.95), rgba(8,10,16,0.95))",
          boxShadow: "0 12px 40px rgba(0,0,0,0.7)",
          border: "1px solid rgba(80,110,150,0.06)",
          color: "#e6eefc",
        }}
      >
        <div style={{ borderBottom: "1px solid rgba(255,255,255,0.03)" }} className="pb-4 mb-4">
          <h3 className="text-2xl font-semibold text-blue-300">{prompt}</h3>
          <p className="text-sm text-gray-300 mt-2">This will be used when Flash Study talks to you.</p>
        </div>

        <div className="flex gap-4 items-center">
          <input
            ref={inputRef}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Enter your name..."
            className="flex-1 bg-transparent border-b border-blue-600 text-white text-lg py-2 px-2 focus:outline-none"
          />

          <button
            onClick={() => onConfirm && onConfirm((name || "").trim() || "Friend")}
            className="px-4 py-2 rounded-md text-white bg-blue-600 hover:bg-blue-500 transition"
          >
            Confirm
          </button>

          <button
            onClick={() => onCancel && onCancel()}
            className="px-4 py-2 rounded-md text-white bg-red-700 hover:bg-red-600 transition"
          >
            Cancel
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}
