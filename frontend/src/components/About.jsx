// src/components/About.jsx
import React, { useEffect } from "react";
import { motion } from "framer-motion";

export default function About({ onBack }) {
  useEffect(() => {
    const handleKey = (e) => {
      if (e.key === "Escape") onBack();
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onBack]);

  return (
    <motion.div
      className="w-full min-h-screen bg-black text-gray-200 px-24 py-20"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.6 }}
    >
      {/* Title */}
      <h1 className="text-5xl font-bold tracking-tight text-blue-400 mb-10">
        Flash Study AI
      </h1>

      {/* Tagline */}
      <p className="text-xl text-gray-400 max-w-4xl mb-12 leading-relaxed">
        An intelligent learning assistant that transforms raw academic material
        into structured, interactive, and personalized study content using
        modern artificial intelligence.
      </p>

      {/* About content */}
      <div className="max-w-5xl space-y-8 text-lg leading-relaxed text-gray-300">
        <p>
          Flash Study AI is designed to address one of the core challenges faced
          by students today — information overload. Traditional study methods
          often require students to manually extract key concepts from lengthy
          documents, which is time-consuming and cognitively demanding.
        </p>

        <p>
          This system automates the learning workflow by converting unstructured
          study materials such as PDFs, lecture notes, and textbooks into
          concise summaries, flashcards, quizzes, mind maps, and semantic search
          results. By leveraging transformer-based Natural Language Processing
          models, Flash Study AI enhances comprehension, retention, and recall.
        </p>

        <p>
          The platform follows a modular architecture with a scalable backend
          and an interactive frontend, enabling future expansion into advanced
          learning tools, collaborative study features, and multi-language
          support.
        </p>
      </div>

      {/* Divider */}
      <div className="my-14 h-px bg-gradient-to-r from-transparent via-blue-900/50 to-transparent" />

      {/* Team Section */}
      <div className="max-w-5xl">
        <h2 className="text-3xl font-semibold text-blue-300 mb-6">
          Project Team
        </h2>

        <p className="text-gray-400 mb-6 text-lg">
          Developed as a final-year academic project by students of the
          Department of Computer Science and Engineering,
          <span className="text-blue-300 font-medium">
            {" "}Saveetha Engineering College
          </span>.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-lg">
          <div className="bg-[#0a0a0f] border border-blue-900/30 rounded-xl p-6">
            <p className="text-blue-400 font-semibold">Melvin S</p>
            <p className="text-gray-400 text-sm mt-1">Team Leader</p>
          </div>

          <div className="bg-[#0a0a0f] border border-blue-900/30 rounded-xl p-6">
            <p className="text-blue-400 font-semibold">Bala Sathiesh C S</p>
            <p className="text-gray-400 text-sm mt-1">Team Member</p>
          </div>

          <div className="bg-[#0a0a0f] border border-blue-900/30 rounded-xl p-6">
            <p className="text-blue-400 font-semibold">Venkatesan M</p>
            <p className="text-gray-400 text-sm mt-1">Team Member</p>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
