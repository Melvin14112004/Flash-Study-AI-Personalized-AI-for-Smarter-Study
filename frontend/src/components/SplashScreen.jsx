// src/components/SplashScreen.jsx
import React, { useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

export default function SplashScreen({ onFinish }) {
  useEffect(() => {
    const timer = setTimeout(onFinish, 5000);
    return () => clearTimeout(timer);
  }, [onFinish]);

  return (
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 flex items-center justify-center bg-black z-50 overflow-hidden"
        initial={{ opacity: 1 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 1.2 }}
      >
        {/* Animated blue mist behind the logo */}
        <motion.div
          className="absolute inset-0 bg-[radial-gradient(circle_at_30%_30%,rgba(0,150,255,0.15),transparent_70%),radial-gradient(circle_at_70%_70%,rgba(0,100,255,0.1),transparent_70%)]"
          animate={{
            backgroundPositionX: ["0%", "100%"],
            backgroundPositionY: ["0%", "100%"],
          }}
          transition={{
            duration: 80,
            repeat: Infinity,
            ease: "linear",
          }}
        />

        {/* Fullscreen logo with glow and fade */}
        <motion.img
          src="/splash-logo.png"
          alt="Flash Study AI Logo"
          className="absolute inset-0 w-full h-full object-cover object-center"
          initial={{ scale: 1.1, opacity: 0 }}
          animate={{
            scale: [1.1, 1.05, 1],
            opacity: [0, 1, 1],
            filter: [
              "drop-shadow(0 0 0px rgba(0,150,255,0))",
              "drop-shadow(0 0 80px rgba(0,150,255,0.4))",
              "drop-shadow(0 0 50px rgba(0,150,255,0.3))"
            ],
          }}
          transition={{ duration: 3.5, ease: "easeInOut" }}
        />
      </motion.div>
    </AnimatePresence>
  );
}
