// src/App.jsx
import React, { useState, useEffect } from "react";
import { AnimatePresence } from "framer-motion";

import SplashScreen from "./components/SplashScreen";
import MainMenu from "./components/MainMenu";
import Hub from "./components/Hub";
import About from "./components/About";

export default function App() {
  const [showSplash, setShowSplash] = useState(true);
  const [mode, setMode] = useState("menu");
  const [currentSave, setCurrentSave] = useState(null);

  // forward active upload ID to Hub/Dashboard (kept for your app)
  const [activeUploadId, setActiveUploadId] = useState(null);

  // NEW: optional opts passed from MainMenu (e.g. { created: true })
  const [activeSaveOpts, setActiveSaveOpts] = useState(null);

  const handleSplashFinish = () => setShowSplash(false);

  const startGame = (saveId, opts = null) => {
    console.log("App: startGame called with:", saveId, opts);
    setCurrentSave(saveId);
    setActiveSaveOpts(opts || null);
    setMode("hub");
  };

  return (
    <div>
      <AnimatePresence mode="wait">
        {showSplash ? (
          <SplashScreen key="splash" onFinish={handleSplashFinish} />

        ) : mode === "menu" ? (
          <MainMenu
            key="menu"
            onStartGame={(id, opts) => startGame(id, opts)}
            onOpenAbout={() => setMode("about")}
          />

        ) : mode === "hub" ? (
          <Hub
            key="hub"
            saveName={currentSave}
            activeSaveOpts={activeSaveOpts}
            // NEW: Hub receives and updates active upload ID
            activeUploadId={activeUploadId}
            onSetActiveUpload={(id) => setActiveUploadId(id)}
            onBack={() => {
              setCurrentSave(null);
              setActiveUploadId(null); // reset on exit
              setActiveSaveOpts(null);
              setMode("menu");
            }}
          />

        ) : (
          <About key="about" onBack={() => setMode("menu")} />
        )}
      </AnimatePresence>
    </div>
  );
}
