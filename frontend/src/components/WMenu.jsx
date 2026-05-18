import React, { useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

export default function WMenu({ open, onClose, onSelect }) {
  useEffect(() => {
    const handler = (e) => {
      if (e.key === "Escape") onClose?.();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            className="fixed inset-0 z-50 bg-black/40"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />

          <motion.nav
            className="fixed left-0 top-0 bottom-0 z-60 w-[320px] max-w-[85%] 
                       bg-[#050506] border-r border-blue-900/40 p-6 backdrop-blur-sm"
            initial={{ x: -360 }}
            animate={{ x: 0 }}
            exit={{ x: -360 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
          >
            <h3 className="text-xl text-blue-300 mb-6 font-semibold">Navigation</h3>

            <ul className="space-y-3 text-gray-300">
              {[
                { k: "dashboard", t: "Dashboard" },
                { k: "mindmaps", t: "Mind Maps" },
                { k: "quiz", t: "Quiz" },
                { k: "flashcards", t: "Flashcards" },
                { k: "settings", t: "Settings" },
                { k: "back", t: "Back to Main Menu" },
              ].map((it) => (
                <li key={it.k}>
                  <button
                    onClick={() => onSelect?.(it.k)}
                    className="w-full text-left px-4 py-2 rounded-md 
                               hover:bg-blue-800/30 transition flex items-center gap-3"
                  >
                    <span className="inline-block w-2 h-2 bg-blue-400 rounded-full" />
                    <span>{it.t}</span>
                  </button>
                </li>
              ))}
            </ul>
          </motion.nav>
        </>
      )}
    </AnimatePresence>
  );
}
