// src/components/Hub.jsx
import React, { useEffect, useState, useCallback, useRef } from "react";
import { motion } from "framer-motion";
import NameModal from "./NameModal";
import Dashboard from "./Dashboard";

export default function Hub({ saveName, onBack, activeSaveOpts = null }) {
  const [optionsOpen, setOptionsOpen] = useState(false);
  const [view, setView] = useState("main");
  const [playerName, setPlayerName] = useState(null);
  const [showNameModal, setShowNameModal] = useState(false);
  const [uploads, setUploads] = useState([]);
  const [activeUploadId, setActiveUploadId] = useState(null);
  const [focusPanel, setFocusPanel] = useState("none");
  const [flashcards, setFlashcards] = useState([]);
  const [flashCount, setFlashCount] = useState(0);
  const [isGenerating, setIsGenerating] = useState(false);
  const [flippedIds, setFlippedIds] = useState(new Set());

  const [mindmap, setMindmap] = useState(null);
  const [mindmapLoading, setMindmapLoading] = useState(false);
  const [mindmapError, setMindmapError] = useState(null);

  const [quiz, setQuiz] = useState(null);
  const [quizLoading, setQuizLoading] = useState(false);
  const [quizError, setQuizError] = useState(null);
  const [quizAnswers, setQuizAnswers] = useState({});
  const [quizSubmitted, setQuizSubmitted] = useState(false);
  const [quizResult, setQuizResult] = useState(null);
  const [quizDifficulty, setQuizDifficulty] = useState(null);

  const [smartQuestion, setSmartQuestion] = useState("");
  const [smartAnswers, setSmartAnswers] = useState([]); // not really used now, kept for safety
  const [smartLoading, setSmartLoading] = useState(false);
  const [smartError, setSmartError] = useState(null);
  const [smartMessages, setSmartMessages] = useState([]); // full chat history

  const storageName = (s) => `save_${s}_player`;
  const navTriggerRef = useRef(null);
  const lastToggleRef = useRef(0);
  const backendOrigin = "http://localhost:5000";

  const prettySaveName = (name) => {
    if (!name) return "";
    const spaced = String(name).replace(/_/g, " ").replace(/\s+/g, " ").trim();
    return spaced
      .split(" ")
      .map((w) => (w ? w.charAt(0).toUpperCase() + w.slice(1) : ""))
      .join(" ");
  };

  useEffect(() => {
    if (!saveName) return;
    const storedPlayer = localStorage.getItem(storageName(saveName));
    setPlayerName(storedPlayer || null);
    const shouldPromptName =
      !storedPlayer && activeSaveOpts && activeSaveOpts.created === true;
    setShowNameModal(Boolean(shouldPromptName));
    setView("main");
    setOptionsOpen(false);
    setFocusPanel("none");
    fetchUploadsFromBackend();
    setFlashcards([]);
    setFlashCount(0);
    setFlippedIds(new Set());
    setMindmap(null);
    setMindmapError(null);
    setQuiz(null);
    setQuizError(null);
    setQuizAnswers({});
    setQuizSubmitted(false);
    setQuizResult(null);
    setQuizDifficulty(null);
    setSmartQuestion("");
    setSmartAnswers([]);
    setSmartLoading(false);
    setSmartError(null);
    setSmartMessages([]);
  }, [saveName, activeSaveOpts]);

  const handleConfirmName = (name) => {
    if (!saveName) return;
    try {
      localStorage.setItem(storageName(saveName), name);
      setPlayerName(name);
      setShowNameModal(false);
    } catch (err) {
      console.error("Hub: failed to save player name", err);
      setPlayerName(name);
      setShowNameModal(false);
    }
  };

  const handleCancelName = () => {
    setShowNameModal(false);
    if (!playerName) setPlayerName("Student");
  };

  const handleKeyDown = useCallback((e) => {
    const now = Date.now();
    if (now - lastToggleRef.current < 300) {
      if (!(e.ctrlKey && e.key && e.key.toLowerCase() === "m")) return;
    }
    if (e.ctrlKey && e.key && e.key.toLowerCase() === "m") {
      e.preventDefault();
      setOptionsOpen((v) => !v);
      lastToggleRef.current = Date.now();
      return;
    }
    if (e.key === "Tab") {
      e.preventDefault();
      setOptionsOpen((v) => !v);
      lastToggleRef.current = Date.now();
      return;
    }
    if (
      (e.key === "Enter" || e.key === " ") &&
      document.activeElement === navTriggerRef.current
    ) {
      e.preventDefault();
      setOptionsOpen((v) => !v);
      lastToggleRef.current = Date.now();
      return;
    }
  }, []);

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown, { passive: false });
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  const fetchUploadsFromBackend = async () => {
    if (!saveName) return [];
    try {
      const res = await fetch(
        `/api/uploads?save_id=${encodeURIComponent(saveName)}`
      );
      const data = await res.json();
      const list = data.uploads || [];
      setUploads(list);
      if (list.length > 0)
        setActiveUploadId((prev) => prev || list[list.length - 1].id);
      return list;
    } catch (err) {
      console.error("Hub: failed to fetch uploads", err);
      return [];
    }
  };

  const addUpload = (uploadMeta, fullList) => {
    if (fullList) {
      setUploads(fullList);
      setActiveUploadId(fullList[fullList.length - 1]?.id || null);
      return;
    }
    setUploads((prev) => {
      const next = [...prev, uploadMeta];
      setActiveUploadId(uploadMeta.id);
      return next;
    });
  };

  const selectUpload = (id) => {
    setActiveUploadId(id);
    setView("main");
    setFocusPanel("none");
    setSmartQuestion("");
    setSmartAnswers([]);
    setSmartLoading(false);
    setSmartError(null);
    setSmartMessages([]);
  };

  const removeUpload = (id) => {
    const next = uploads.filter((u) => u.id !== id);
    setUploads(next);
    if (activeUploadId === id)
      setActiveUploadId(next.length ? next[next.length - 1].id : null);
  };

  const activeUpload =
    uploads.find((u) => u.id === activeUploadId) || null;

  const genStatusFor = (upload) => {
    const flash = !!upload.flashcards_generated;
    const mind = !!upload.mindmap_generated;
    const quiz = !!upload.quiz_generated;
    const score = upload.quiz_score ?? null;
    const total = 3;
    const done = [flash, mind, quiz].filter(Boolean).length;
    const pct = Math.round((done / total) * 100);
    return { flash, mind, quiz, score, done, total, pct };
  };

  const displayNameNoExt = (filename) => {
    if (!filename) return "";
    return String(filename).replace(/\.[^/.]+$/, "");
  };

  async function handlePlayAudio() {
    if (!activeUpload) return alert("Select an upload first.");
    const pdfId = activeUpload.id || activeUpload.pdf_id;
    if (!pdfId) return alert("Could not determine upload id.");
    const saveEnc = encodeURIComponent(saveName);
    const pdfEnc = encodeURIComponent(pdfId);
    try {
      const genUrl = `${backendOrigin}/save/${saveEnc}/${pdfEnc}/tts`;
      const res = await fetch(genUrl, { method: "POST" });
      const ct = res.headers.get("content-type") || "";
      if (res.ok && ct.startsWith("audio/")) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        await audio
          .play()
          .catch((e) => {
            console.error("Playback error:", e);
            alert("Playback failed.");
          });
        return;
      }
      const text = await res.text().catch(() => "");
      let body = null;
      try {
        body = text ? JSON.parse(text) : null;
      } catch (e) {
        body = null;
      }
      if (!res.ok) {
        console.warn("TTS POST failed", res.status, body || text);
        await fetchUploadsFromBackend();
        alert(body?.message || "TTS generation failed/queued. Check server logs.");
        return;
      }
      const filename = body?.tts_file || body?.audio_file || null;
      if (filename) {
        const audioUrl = `${backendOrigin}/saves/${saveEnc}/tts/${encodeURIComponent(
          filename
        )}`;
        try {
          const a = new Audio(audioUrl);
          await a.play();
          return;
        } catch (err) {
          console.warn("Direct play failed, trying fetch+blob:", err);
          try {
            const r2 = await fetch(audioUrl);
            if (
              r2.ok &&
              (r2.headers.get("content-type") || "").startsWith("audio/")
            ) {
              const b = await r2.blob();
              const u = URL.createObjectURL(b);
              const a2 = new Audio(u);
              await a2.play();
              return;
            }
          } catch (e) {
            console.warn("fetch audio failed:", e);
          }
        }
      }
      const serveUrl = `${backendOrigin}/api/upload/${pdfEnc}/tts?save_id=${saveEnc}`;
      try {
        const r = await fetch(serveUrl);
        if (r.ok) {
          const ctype = r.headers.get("content-type") || "";
          if (ctype.startsWith("audio/")) {
            const blob = await r.blob();
            const u = URL.createObjectURL(blob);
            const audio = new Audio(u);
            await audio.play();
            return;
          }
        }
      } catch (e) {
        console.warn("serve endpoint error:", e);
      }
      await fetchUploadsFromBackend();
      alert("TTS requested/queued. Try Play again in a few seconds.");
    } catch (err) {
      console.error("handlePlayAudio error:", err);
      alert("Failed to request/play TTS. See console for details.");
    }
  }

  function deriveAnswer(frontText) {
    if (!frontText) return "—";
    const m = frontText.match(
      /\b(?:is|are|means|refers to|called)\s+(?:an|a|the)?\s*([^.,;]+)/i
    );
    if (m && m[1]) return m[1].trim();
    const p = frontText.match(/\(([^)]+)\)/);
    if (p) return p[1].trim();
    const afterColon = frontText.split(/[:\-–—]/).pop().trim();
    if (afterColon && afterColon.split(/\s+/).length <= 8) return afterColon;
    const ex = frontText.split(/for example|e\.g\.|eg\./i);
    if (ex.length > 1) {
      const candidate = ex[1].split(/[.,;]/)[0].trim();
      if (candidate) return candidate;
    }
    const words = frontText
      .replace(/[^\w\s]/g, "")
      .split(/\s+/)
      .filter(Boolean);
    if (words.length <= 8) return frontText;
    return words.slice(-3).join(" ");
  }

  const fetchFlashcards = async () => {
    if (!activeUpload || !saveName) return;
    try {
      const id = encodeURIComponent(activeUpload.id || activeUpload.pdf_id);
      const s = encodeURIComponent(saveName);
      const res = await fetch(
        `${backendOrigin}/api/upload/${id}/flashcards?save_id=${s}`
      );
      if (!res.ok) {
        console.warn(
          "fetchFlashcards non-ok",
          res.status,
          await res.text().catch(() => "")
        );
        setFlashcards([]);
        setFlashCount(0);
        return;
      }
      const j = await res.json();
      const data = j.flashcards || j.flashcards || [];
      const normalized = (Array.isArray(data) ? data : []).map((fc, idx) => {
        const front = (fc.front || fc.q || fc.question || "").trim();
        const back = (fc.back || fc.a || fc.answer || "").trim();
        const id = fc.id || `fc_${idx + 1}`;
        let finalBack = back;
        if (!finalBack) finalBack = deriveAnswer(front);
        else if (finalBack === front) finalBack = deriveAnswer(front);
        return { id, front: front || "—", back: finalBack || "—" };
      });
      setFlashcards(normalized);
      setFlashCount(normalized.length);
      setFlippedIds(new Set());
    } catch (err) {
      console.error("fetchFlashcards error:", err);
      setFlashcards([]);
      setFlashCount(0);
    }
  };

  const generateFlashcards = async () => {
    if (!activeUpload || !saveName) return alert("Select an upload first.");
    setIsGenerating(true);
    try {
      const id = encodeURIComponent(activeUpload.id || activeUpload.pdf_id);
      const s = encodeURIComponent(saveName);
      const res = await fetch(
        `${backendOrigin}/api/upload/${id}/generate_flashcards?save_id=${s}`,
        { method: "POST" }
      );
      const text = await res.text().catch(() => "");
      let body = null;
      try {
        body = text ? JSON.parse(text) : null;
      } catch (e) {
        body = null;
      }
      if (!res.ok) {
        console.warn("generateFlashcards failed", res.status, body || text);
        alert(body?.message || "Flashcards generation failed. See console.");
        setIsGenerating(false);
        return;
      }
      await fetchFlashcards();
      setIsGenerating(false);
    } catch (err) {
      console.error("generateFlashcards error:", err);
      alert("Flashcards generation failed. See console.");
      setIsGenerating(false);
    }
  };

  const toggleFlip = (id) => {
    setFlippedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  function extractKeyword(text) {
    if (!text) return "Topic";
    const capMatch = text.match(/\b([A-Z][a-z]{3,})\b/);
    if (capMatch) return capMatch[1];
    const aboutMatch = text.match(
      /\b(?:about|on|of|regarding|concerning)\s+([A-Za-z0-9 ]{3,40})/i
    );
    if (aboutMatch)
      return aboutMatch[1].split(/\s+/).slice(0, 2).join(" ");
    const words = text
      .replace(/[^\w\s]/g, "")
      .split(/\s+/)
      .filter((w) => w.length > 2);
    if (words.length === 0) return "Topic";
    return words.length === 1 ? words[0] : words[0] + " " + words[1];
  }

  const fetchMindmap = async (force = false) => {
    setMindmapLoading(true);
    setMindmapError(null);
    setMindmap(null);

    if (!activeUpload) {
      setMindmapError("Select an upload first.");
      setMindmapLoading(false);
      return;
    }

    const uploadId = encodeURIComponent(activeUpload.id || activeUpload.pdf_id);
    const saveEnc = encodeURIComponent(saveName);
    const url = `${backendOrigin}/api/upload/${uploadId}/mindmap?save_id=${saveEnc}`;

    try {
      const res = await fetch(url, { method: "GET" });
      if (!res.ok) {
        const txt = await res.text().catch(() => "");
        console.warn("Mindmap GET non-ok", res.status, txt);
        setMindmapLoading(false);
        return;
      }
      const body = await res.json();
      const data = body.mindmap || body || null;
      if (!data) {
        setMindmapError("Mindmap returned unexpected payload.");
        setMindmapLoading(false);
        return;
      }

      const normalized = {
        root:
          data.root ||
          data.title ||
          data.label ||
          (activeUpload
            ? displayNameNoExt(activeUpload.name) || saveName
            : saveName),
        sections: Array.isArray(data.sections)
          ? data.sections.slice(0, 8).map((s, i) => ({
              id: s.id || `s${i + 1}`,
              title: (s.title || s.label || "").trim(),
              content: (s.content || s.description || "").trim(),
            }))
          : [],
      };

      if (
        (!normalized.sections || normalized.sections.length === 0) &&
        activeUpload &&
        (activeUpload.summary || activeUpload.short)
      ) {
        const txt = (activeUpload.summary || activeUpload.short || "")
          .replace(/\s+/g, " ")
          .trim();
        const sentences = txt
          .split(/(?<=[.!?])\s+/)
          .filter(Boolean)
          .slice(0, 6);
        normalized.sections = sentences.map((s, i) => ({
          id: `s${i + 1}`,
          title: s.slice(0, 80),
          content: s,
        }));
      }

      normalized.sections = normalized.sections.map((sec) => ({
        ...sec,
        keyword: extractKeyword(sec.title || sec.content || ""),
      }));

      setMindmap(normalized);
    } catch (err) {
      console.error("fetchMindmap error:", err);
      setMindmapError("Failed to load mindmap. See console.");
    } finally {
      setMindmapLoading(false);
    }
  };

  const generateMindmap = async () => {
    if (!activeUpload) return alert("Select an upload first.");
    setMindmapLoading(true);
    setMindmapError(null);
    const uploadId = encodeURIComponent(activeUpload.id || activeUpload.pdf_id);
    const saveEnc = encodeURIComponent(saveName);
    const apiUrl = `${backendOrigin}/api/upload/${uploadId}/generate_mindmap?save_id=${saveEnc}`;
    const legacyUrl = `${backendOrigin}/save/${saveEnc}/${uploadId}/generate_mindmap`;
    try {
      let res = await fetch(apiUrl, { method: "POST" });
      if (res.status === 405 || res.status === 404) {
        res = await fetch(legacyUrl, { method: "POST" });
      }
      if (!res.ok) {
        const txt = await res.text().catch(() => "");
        console.warn("generateMindmap non-ok", res.status, txt);
        setMindmapError(
          `Generation failed (status ${res.status}). Check server logs.`
        );
        setMindmapLoading(false);
        return;
      }
      await fetchUploadsFromBackend();
      setTimeout(() => fetchMindmap(true), 700);
    } catch (err) {
      console.error("generateMindmap error:", err);
      setMindmapError("Generation failed. See console.");
      setMindmapLoading(false);
    }
  };

  const fetchQuiz = async () => {
    if (!activeUpload || !saveName) return;
    try {
      const uploadId = encodeURIComponent(activeUpload.id || activeUpload.pdf_id);
      const s = encodeURIComponent(saveName);
      const res = await fetch(
        `${backendOrigin}/api/upload/${uploadId}/quiz?save_id=${s}`
      );
      if (!res.ok) {
        const txt = await res.text().catch(() => "");
        console.warn("quiz GET non-ok", res.status, txt);
        setQuizError("Failed to load quiz.");
        return;
      }
      const body = await res.json();
      const data = body.quiz || body;
      setQuiz(data || { questions: [] });
    } catch (err) {
      console.error("fetchQuiz error:", err);
      setQuizError("Failed to load quiz.");
    }
  };

  const generateQuiz = async (difficulty) => {
    if (!activeUpload || !saveName) {
      alert("Select an upload first.");
      return;
    }
    setQuizLoading(true);
    setQuizError(null);
    setQuiz(null);
    setQuizAnswers({});
    setQuizSubmitted(false);
    setQuizResult(null);
    setQuizDifficulty(difficulty);
    try {
      const uploadId = encodeURIComponent(activeUpload.id || activeUpload.pdf_id);
      const s = encodeURIComponent(saveName);
      const res = await fetch(
        `${backendOrigin}/api/upload/${uploadId}/generate_quiz?save_id=${s}&difficulty=${encodeURIComponent(
          difficulty
        )}`,
        { method: "POST" }
      );
      if (!res.ok) {
        const txt = await res.text().catch(() => "");
        console.warn("generateQuiz non-ok", res.status, txt);
        setQuizError("Quiz generation failed. Check server logs.");
        setQuizLoading(false);
        return;
      }
      await fetchQuiz();
    } catch (err) {
      console.error("generateQuiz error:", err);
      setQuizError("Quiz generation failed.");
    } finally {
      setQuizLoading(false);
    }
  };

  const handleQuizOptionChange = (qid, idx) => {
    setQuizAnswers((prev) => ({ ...prev, [qid]: idx }));
  };

  const handleQuizSubmit = () => {
    if (!quiz || !quiz.questions || quiz.questions.length === 0) return;
    let correct = 0;
    const details = quiz.questions.map((q) => {
      const chosen = quizAnswers[q.id];
      const correctIdx =
        typeof q.answer_index === "number" ? q.answer_index : 0;
      const isCorrect = chosen === correctIdx;
      if (isCorrect) correct += 1;
      return { id: q.id, chosen, correctIdx, isCorrect };
    });
    setQuizSubmitted(true);
    setQuizResult({
      total: quiz.questions.length,
      correct,
      wrong: quiz.questions.length - correct,
      details,
    });
  };

  const sanitizeSmartInput = (text) => {
  if (!text) return "";
  // Remove long instruction blocks and common templates users paste
  let out = text
    .replace(/Answer the student's question[\s\S]*?notes below[:]?/gi, "")
    .replace(/Use only the notes below[\s\S]*$/gi, "")
    .replace(/You are a helpful (study )?assistant[.]*[\s\S]*?$/gi, "")
    .replace(/If the answer is not present[\s\S]*?re-?read/gi, "")
    .replace(/Here is some background from the student's PDF[:]?/gi, "")
    .replace(/Here is some background from[:]?/gi, "")
    .replace(/\s{2,}/g, " ")
    .trim();
  // Strip wrapping quotes if user pasted whole blocks
  out = out.replace(/^["“”']+|["“”']+$/g, "");
  return out;
  };


  const handleSmartAsk = async () => {
  if (!activeUpload || !saveName) return;

  const raw = smartQuestion.trim();
  const cleaned = sanitizeSmartInput(raw);

  if (!cleaned) {
    alert("Please type only your question.");
    return;
  }

  // add user message to chat immediately
  const newUserMsg = { role: "user", text: cleaned };
  const historyForBackend = [...smartMessages, newUserMsg].map(m => ({
    role: m.role,
    content: m.text,
  }));

  setSmartMessages(prev => [...prev, newUserMsg]);
  setSmartLoading(true);
  setSmartError(null);

  try {
    const uploadId = encodeURIComponent(activeUpload.id);
    const s = encodeURIComponent(saveName);

    const res = await fetch(
      `${backendOrigin}/api/upload/${uploadId}/smart?save_id=${s}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: cleaned,
          history: historyForBackend,   // <-- send history
        }),
      }
    );

    if (!res.ok) {
      const txt = await res.text().catch(() => "");
      console.warn("smart search non-ok", res.status, txt);
      setSmartError("Failed to get answer.");
      return;
    }

    const body = await res.json();
    const ans = body.answer || "Sorry, I couldn't understand that.";

    // add assistant answer to chat
    setSmartMessages(prev => [...prev, { role: "assistant", text: ans }]);
    setSmartQuestion(""); // clear input
  } catch (err) {
    console.error("Smart search error:", err);
    setSmartError("Smart search failed.");
  } finally {
    setSmartLoading(false);
  }
};

  const handleOptionSelect = (key) => {
    setOptionsOpen(false);
    if (key === "main") return onBack?.();
    if (key === "dashboard") {
      setView("dashboard");
      return;
    }
    if (key === "flashcards") {
      if (!activeUpload) {
        alert("No upload selected. Go to Dashboard first.");
        return;
      }
      setView("main");
      setFocusPanel("flashcards");
      fetchFlashcards();
      return;
    }
    if (key === "mindmap") {
      if (!activeUpload) {
        alert("No upload selected. Go to Dashboard first.");
        return;
      }
      setView("main");
      setFocusPanel("mindmap");
      setMindmap(null);
      setMindmapError(null);
      fetchMindmap();
      return;
    }
    if (key === "quiz") {
      if (!activeUpload) {
        alert("No upload selected. Go to Dashboard first.");
        return;
      }
      setView("main");
      setFocusPanel("quiz");
      setQuiz(null);
      setQuizError(null);
      setQuizAnswers({});
      setQuizSubmitted(false);
      setQuizResult(null);
      setQuizDifficulty(null);
      return;
    }
  };

  function MindmapNode({ node, upload }) {
    if (!node) return null;

    const stripUuid = (s) =>
      String(s || "")
        .replace(/\b[0-9a-fA-F\-]{6,}\b/g, "")
        .replace(/__+/g, " ")
        .replace(/_/g, " ")
        .trim();

    const rootLabel =
      stripUuid(
        node.root ||
          node.title ||
          node.label ||
          (upload ? displayNameNoExt(upload.name) || "" : "")
      ) || "Document";

    const sections = (node.sections || []).slice(0, 16);
    const radiusPct = 58;
    const n = Math.max(sections.length, 1);
    const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

    const computed = sections.map((s, i) => {
      const angle = (i / n) * Math.PI * 2 - Math.PI / 2;
      const rawLeft = 50 + Math.cos(angle) * radiusPct;
      const rawTop = 50 + Math.sin(angle) * radiusPct;
      const boxW = 20;
      const boxH = 18;
      let left = clamp(rawLeft, 6 + boxW / 2, 94 - boxW / 2);
      let top = clamp(rawTop, 8 + boxH / 2, 92 - boxH / 2);
      if (left > 60) left = Math.min(96 - boxW / 2, left + 2);
      if (left < 40) left = Math.max(6 + boxW / 2, left - 2);
      let transform = "translate(-50%, -50%)";
      if (left <= 12) transform = "translate(0, -50%)";
      else if (left >= 88) transform = "translate(-100%, -50%)";
      return { s, left, top, transform, angle };
    });

    return (
      <div
        style={{
          width: "100%",
          height: 460,
          position: "relative",
          marginTop: 6,
        }}
      >
        <div
          style={{
            position: "absolute",
            inset: 6,
            borderRadius: 18,
            pointerEvents: "none",
            boxShadow: "inset 0 0 0 1px rgba(255,255,255,0.02)",
            border: "1px solid rgba(74,163,255,0.04)",
            zIndex: 0,
          }}
        />
        <div
          style={{
            position: "absolute",
            inset: 14,
            borderRadius: 14,
            background: "#ffffff",
            boxShadow: "0 8px 30px rgba(0,0,0,0.45)",
            zIndex: 1,
          }}
        />
        <svg
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            pointerEvents: "none",
            zIndex: 2,
          }}
        >
          {computed.map((c, i) => (
            <line
              key={`l-${c.s.id || i}`}
              x1={50}
              y1={50}
              x2={c.left}
              y2={c.top}
              stroke="#000"
              strokeWidth={0.9}
              strokeLinecap="round"
            />
          ))}
        </svg>

        <div
          style={{
            position: "absolute",
            left: "50%",
            top: "50%",
            transform: "translate(-50%, -50%)",
            padding: "10px 14px",
            borderRadius: 14,
            background: "linear-gradient(90deg,#cfe8ff,#e8f9ff)",
            color: "#022230",
            fontWeight: 800,
            textAlign: "center",
            boxShadow: "0 14px 36px rgba(6,18,30,0.6)",
            maxWidth: 200,
            wordBreak: "break-word",
            zIndex: 5,
          }}
        >
          {rootLabel}
        </div>

        {computed.map((c, i) => {
          const label = (
            (c.s && c.s.content) ||
            c.s.title ||
            "Topic"
          )
            .toString()
            .trim()
            .split(/\s+/)
            .slice(0, 2)
            .join(" ");
          return (
            <div
              key={c.s.id || i}
              style={{
                position: "absolute",
                left: `${c.left}%`,
                top: `${c.top}%`,
                transform: c.transform,
                minWidth: 120,
                maxWidth: 140,
                cursor: "default",
                zIndex: 6,
              }}
            >
              <div
                style={{
                  padding: 10,
                  borderRadius: 12,
                  background: "linear-gradient(180deg, #6ecbff, #42b7ff)",
                  border: "1px solid rgba(0,0,0,0.08)",
                  color: "#022230",
                  boxShadow: "0 10px 22px rgba(0,0,0,0.6)",
                  minHeight: 48,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  overflow: "hidden",
                }}
              >
                <span
                  style={{
                    fontWeight: 900,
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}
                >
                  {label}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    );
  }

  const css = `
    .hub-root {
      min-height: 100vh;
      position: relative;
      overflow: auto;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial;
      color: #e6f3ff;
      background:
        linear-gradient(180deg, rgba(3,8,12,0.55), rgba(0,0,0,0.75)),
        url('/hub.jpg') center/cover no-repeat;
      padding: 20px;
    }
    .hub-root::before {
      content: "";
      position: absolute;
      inset: 0;
      pointer-events: none;
      background: radial-gradient(ellipse at center, rgba(0,0,0,0) 40%, rgba(0,0,0,0.55) 100%);
    }
    .hub-root::after {
      content: "";
      position: absolute;
      inset: 0;
      pointer-events: none;
      background: linear-gradient(180deg, rgba(74,163,255,0.02), rgba(10,60,90,0.02));
    }

    .summary-content, .hs-flashcards, .summary-inner {
      overflow-y: auto;
      -ms-overflow-style: none;
      scrollbar-width: none;
    }
    .summary-content::-webkit-scrollbar, .hs-flashcards::-webkit-scrollbar, .summary-inner::-webkit-scrollbar {
      display: none;
      width: 0;
      height: 0;
    }

    .quiz-scroll {
      overflow-y: auto;
      -ms-overflow-style: none;
      scrollbar-width: none;
    }
    .quiz-scroll::-webkit-scrollbar {
      display: none;
      width: 0;
      height: 0;
    }

    .options-panel {
      position: fixed;
      left: 0;
      top: 0;
      height: 100%;
      width: 220px;
      padding: 14px;
      transform: translateX(-95%);
      transition: transform .18s;
      background: #000;
      border-right: 1px solid rgba(255,255,255,0.04);
      box-shadow: inset -12px 0 24px rgba(0,0,0,0.6), 0 10px 30px rgba(0,0,0,0.6);
      z-index: 220;
      color: #9fbfe6;
      display: flex;
      flex-direction: column;
      border-top-right-radius: 12px;
      border-bottom-right-radius: 12px;
    }
    .options-panel.open { transform: translateX(0); }
    .options-panel .opt-title { color: #ffffff; font-weight: 700; margin-bottom: 12px; font-size: 18px; }

    .glass {
      background: #000;
      border: 1px solid rgba(255,255,255,0.04);
      border-radius: 12px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.7);
    }
    .card {
      background: #000;
      border-radius: 10px;
      border: 1px solid rgba(255,255,255,0.03);
      padding: 12px;
    }
    .btn {
      border-radius: 8px;
      padding: 8px 12px;
      cursor: pointer;
      border: none;
      font-weight: 600;
    }
    .btn.btn-accent {
      background: linear-gradient(180deg,#4aa3ff,#1f88ff);
      color: #021627;
      box-shadow: 0 6px 18px rgba(31,136,255,0.08);
      border: none;
    }
    .btn-muted {
      background: #101214;
      color: #cfe8ff;
      border: 1px solid rgba(255,255,255,0.02);
    }

    .options-panel .btn:hover {
      background: linear-gradient(180deg, #4aa3ff, #1f88ff);
      color: #021627;
    }
    .options-panel .btn:disabled,
    .options-panel .btn[disabled] {
      opacity: 0.6;
      cursor: default;
      background: #101214;
      color: #7faecf;
    }

    .summary-outer {
      background: transparent;
      border-radius: 10px;
      padding: 0;
    }

    .summary-inner {
      background: #f3f4f6;
      color: #0b0b0b;
      border-radius: 10px;
      padding: 14px;
      box-shadow: 0 6px 14px rgba(0,0,0,0.09), inset 0 1px 0 rgba(255,255,255,0.6);
      border: 1px solid rgba(0,0,0,0.08);
      max-height: 720px;
      overflow-y: auto;
      line-height: 1.6;
      white-space: pre-line;
    }

    .flashcards-box {
      background: rgba(0, 0, 0, 0.55);
      border: 1px solid rgba(255,255,255,0.05);
      padding: 12px;
      border-radius: 12px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.65);
      height: calc(100vh - 220px);
    }

    .flashcard-card {
      background: #f3f4f6;
      border: 1px solid rgba(0,0,0,0.08);
      padding: 12px;
      border-radius: 10px;
      min-height: 100%;
      box-shadow: 0 6px 14px rgba(0,0,0,0.09), inset 0 1px 0 rgba(255,255,255,0.6);
    }

    .q-label { color: #4aa3ff; font-weight: 700; font-size: 12px; }
    .qa-text { color: #0b0b0b; font-size: 14px; line-height: 1.5; }

    @media (max-width: 920px) {
      .grid-2col { grid-template-columns: 1fr !important; }
      .summary-inner { max-height: 420px; }
      .hs-flashcards { max-height: 56vh; }
    }
  `;

  const cardOuter = { perspective: "1000px" };
  const cardInner = (flipped) => ({
    transformStyle: "preserve-3d",
    transform: flipped ? "rotateY(180deg)" : "rotateY(0deg)",
    transition: "transform 0.45s cubic-bezier(.2,.9,.3,1)",
    position: "relative",
    height: "100%",
  });
  const faceCommon = {
    backfaceVisibility: "hidden",
    WebkitBackfaceVisibility: "hidden",
    position: "absolute",
    inset: 0,
    padding: "12px",
    borderRadius: 10,
    display: "flex",
    flexDirection: "column",
  };
  const backFace = { ...faceCommon, transform: "rotateY(180deg)" };
  const accent = "#4aa3ff";
  const gold = "#ffffff";

  return (
    <div className="hub-root">
      <style>{css}</style>
      <button
        ref={navTriggerRef}
        aria-label="Open options"
        className="sr-only"
        style={{ position: "absolute", left: -9999 }}
      />

      <div
        className={`options-panel ${optionsOpen ? "open" : ""}`}
        aria-hidden={!optionsOpen}
      >
        <div className="opt-title">Options</div>

        <button
          onClick={() => handleOptionSelect("dashboard")}
          className="btn btn-muted"
          style={{
            width: "100%",
            textAlign: "left",
            padding: "8px 10px",
            borderRadius: 8,
            marginBottom: 8,
          }}
        >
          Dashboard
        </button>

        <button
          onClick={() => handleOptionSelect("flashcards")}
          disabled={!activeUpload}
          className="btn btn-muted"
          style={{
            width: "100%",
            textAlign: "left",
            padding: "8px 10px",
            borderRadius: 8,
            marginBottom: 8,
            opacity: activeUpload ? 1 : 0.6,
          }}
        >
          Flashcards
        </button>

        <button
          onClick={() => handleOptionSelect("mindmap")}
          disabled={!activeUpload}
          className="btn btn-muted"
          style={{
            width: "100%",
            textAlign: "left",
            padding: "8px 10px",
            borderRadius: 8,
            marginBottom: 8,
            opacity: activeUpload ? 1 : 0.6,
          }}
        >
          Mindmap
        </button>

        <button
          onClick={() => handleOptionSelect("quiz")}
          disabled={!activeUpload}
          className="btn btn-muted"
          style={{
            width: "100%",
            textAlign: "left",
            padding: "8px 10px",
            borderRadius: 8,
            marginBottom: 8,
            opacity: activeUpload ? 1 : 0.6,
          }}
        >
          Quiz
        </button>

        <button
          onClick={() => handleOptionSelect("main")}
          className="btn btn-muted"
          style={{
            width: "100%",
            textAlign: "left",
            padding: "8px 10px",
            borderRadius: 8,
            marginTop: 12,
          }}
        >
          Main Menu
        </button>
      </div>

      <NameModal
        open={showNameModal}
        initial={playerName || ""}
        prompt={`Welcome — ${prettySaveName(saveName)}`}
        onConfirm={handleConfirmName}
        onCancel={handleCancelName}
      />

      {view === "dashboard" ? (
        <Dashboard
          saveName={saveName}
          uploads={uploads}
          onAddUpload={addUpload}
          onSelectUpload={selectUpload}
          onRemoveUpload={removeUpload}
          onBack={() => setView("main")}
        />
      ) : (
        <div
          style={{
            maxWidth: 1400,
            margin: "0 auto",
            display: "grid",
            gridTemplateColumns: "1.2fr 1fr",
            gap: 20,
          }}
          className="grid-2col"
        >
          <div>
            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className="glass"
              style={{ padding: 22 }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                }}
              >
                <div>
                  <h1
                    style={{
                      fontSize: 34,
                      color: accent,
                      margin: 0,
                      fontWeight: 700,
                    }}
                  >
                    Welcome{playerName ? `, ${playerName}` : ""}
                  </h1>
                  <b style={{ color: "#cfe8ff", marginTop: 6 }}>
                    Subject:{" "}
                    <span style={{ color: gold }}>
                      {prettySaveName(saveName)}
                    </span>
                  </b>
                </div>

                <button
                  onClick={() => setView("dashboard")}
                  className="btn btn-accent"
                >
                  Go to Dashboard
                </button>
              </div>

              <div
                style={{ marginTop: 18, borderRadius: 10, padding: 18 }}
                className="card"
              >
                {!activeUpload ? (
                  <p style={{ color: "#9fbfe6" }}>
                    No PDF selected. Open Dashboard to upload or choose one.
                  </p>
                ) : (
                  <>
                    <p
                      style={{
                        fontWeight: 600,
                        color: "#e6f6ff",
                        marginBottom: 6,
                      }}
                    >
                      {displayNameNoExt(activeUpload.name)}
                    </p>

                    <div
                      className="summary-content summary-outer"
                      style={{ marginTop: 6, maxHeight: 720 }}
                    >
                      <div className="summary-inner">
                        {activeUpload.summary || "Summary Loading."}
                      </div>
                    </div>

                    <div
                      style={{
                        marginTop: 14,
                        display: "flex",
                        gap: 10,
                        flexWrap: "wrap",
                      }}
                    >
                      <button
                        onClick={() => {
                          setFocusPanel("smart");
                          setSmartError(null);
                          // keep messages so chat is persistent
                        }}
                        className="btn btn-accent"
                      >
                        Smart Search
                      </button>

                      <button
                        onClick={async () => {
                          await handlePlayAudio();
                        }}
                        className="btn btn-accent"
                      >
                        Play Audio
                      </button>

                      <button
                        onClick={async () => {
                          try {
                            const text =
                              activeUpload.summary || activeUpload.short || "";
                            if (!text) return;
                            await navigator.clipboard.writeText(text);
                          } catch (err) {
                            console.error("Copy failed:", err);
                          }
                        }}
                        className="btn btn-accent"
                      >
                        Copy Summary
                      </button>
                    </div>
                  </>
                )}
              </div>
            </motion.div>
          </div>

          <div>
            {focusPanel === "none" ? (
              <div
                className="glass"
                style={{
                  height: "100%",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#9fbfe6",
                  padding: 18,
                }}
              >
                Select a tool from Options
              </div>
            ) : focusPanel === "flashcards" ? (
              <motion.div
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                className="glass"
                style={{
                  padding: 16,
                  maxHeight: "calc(100vh - 120px)",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: 12,
                  }}
                >
                  <b style={{ color: gold, margin: 0 }}>Flashcards</b>
                  <div style={{ color: "#9fbfe6", fontSize: 13 }}>
                    Generated {flashCount}
                  </div>
                </div>

                <div style={{ display: "flex", gap: 10, marginBottom: 12 }}>
                  <button
                    onClick={generateFlashcards}
                    disabled={isGenerating}
                    className="btn btn-accent"
                  >
                    {isGenerating ? "Generating..." : "Generate Flashcards"}
                  </button>
                </div>

                <div className="flashcards-box">
                  <div
                    className="hs-flashcards"
                    style={{
                      overflowY: "auto",
                      maxHeight: "100%",
                      display: "flex",
                      flexDirection: "column",
                      gap: 16,
                      paddingRight: 6,
                    }}
                  >
                    {flashcards.length === 0 ? (
                      <div style={{ color: "#1f3b3f" }}>
                        No flashcards available. Click Generate.
                      </div>
                    ) : (
                      flashcards.map((fc, idx) => {
                        const id = fc.id || `fc_${idx + 1}`;
                        const flipped = flippedIds.has(id);
                        return (
                          <div key={id} style={cardOuter}>
                            <div
                              style={{
                                position: "relative",
                                height: 140,
                                cursor: "pointer",
                              }}
                              onClick={() => toggleFlip(id)}
                            >
                              <div style={cardInner(flipped)}>
                                <div
                                  style={{ ...faceCommon }}
                                  className="flashcard-card"
                                >
                                  <div className="q-label">Q</div>
                                  <div
                                    className="qa-text"
                                    style={{ marginTop: 8 }}
                                  >
                                    {fc.front}
                                  </div>
                                </div>

                                <div
                                  style={{ ...backFace }}
                                  className="flashcard-card"
                                >
                                  <div className="q-label">A</div>
                                  <div
                                    className="qa-text"
                                    style={{ marginTop: 8 }}
                                  >
                                    {fc.back}
                                  </div>
                                </div>
                              </div>
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>
              </motion.div>
            ) : focusPanel === "mindmap" ? (
              <motion.div
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                className="glass"
                style={{
                  padding: 16,
                  maxHeight: "calc(100vh - 120px)",
                  overflow: "auto",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: 12,
                  }}
                >
                  <b style={{ color: gold, margin: 0 }}>Mindmap</b>
                  <div style={{ display: "flex", gap: 8 }}>
                    <button
                      onClick={() => generateMindmap()}
                      className="btn btn-accent"
                    >
                      Generate
                    </button>
                  </div>
                </div>

                {mindmapLoading && (
                  <div style={{ color: "#9fbfe6" }}>Loading mindmap…</div>
                )}
                {mindmapError && (
                  <div style={{ color: "#ffb4b4" }}>{mindmapError}</div>
                )}

                {!mindmapLoading && !mindmapError && mindmap && (
                  <div style={{ marginTop: 8 }}>
                    <MindmapNode node={mindmap} upload={activeUpload} />
                  </div>
                )}

                {!mindmapLoading && !mindmap && !mindmapError && (
                  <div style={{ color: "#9fbfe6" }}>
                    No mindmap available. Click Generate to create one.
                  </div>
                )}
              </motion.div>
            ) : focusPanel === "quiz" ? (
              <motion.div
                className="glass"
                style={{
                  padding: 16,
                  maxHeight: "calc(100vh - 120px)",
                  display: "flex",
                  flexDirection: "column",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: 10,
                  }}
                >
                  <b style={{ color: gold }}>Quiz</b>
                  <span style={{ fontSize: 13, color: "#9fbfe6" }}>
                    {quizDifficulty
                      ? `Difficulty: ${quizDifficulty.toUpperCase()}`
                      : "Choose difficulty"}
                  </span>
                </div>

                <div
                  style={{
                    display: "flex",
                    gap: 8,
                    marginBottom: 12,
                  }}
                >
                  {["easy", "medium", "hard"].map((lv) => (
                    <button
                      key={lv}
                      onClick={() => generateQuiz(lv)}
                      disabled={quizLoading}
                      className="btn btn-accent"
                      style={{
                        opacity: quizLoading ? 0.7 : 1,
                        border:
                          quizDifficulty === lv
                            ? "2px solid #ffffff"
                            : "none",
                      }}
                    >
                      {lv.charAt(0).toUpperCase() + lv.slice(1)}
                    </button>
                  ))}
                </div>

                {quizLoading && (
                  <div
                    style={{ color: "#9fbfe6", marginBottom: 8 }}
                  >
                    Generating quiz…
                  </div>
                )}
                {quizError && (
                  <div
                    style={{ color: "#ffb4b4", marginBottom: 8 }}
                  >
                    {quizError}
                  </div>
                )}

                <div
                  className="quiz-scroll"
                  style={{ flex: 1, paddingRight: 6 }}
                >
                  {!quizLoading &&
                    !quizError &&
                    (!quiz ||
                      !quiz.questions ||
                      quiz.questions.length === 0) && (
                      <div style={{ color: "#9fbfe6" }}>
                        No quiz yet. Choose a difficulty to generate.
                      </div>
                    )}

                  {quiz &&
                    quiz.questions &&
                    quiz.questions.length > 0 && (
                      <div
                        style={{
                          display: "flex",
                          flexDirection: "column",
                          gap: 10,
                        }}
                      >
                        {(() => {
                          const mapResult = quizResult
                            ? Object.fromEntries(
                                quizResult.details.map((d) => [
                                  d.id,
                                  d,
                                ])
                              )
                            : {};
                          const baseQuestions = quiz.questions || [];
                          let viewQuestions = baseQuestions;
                          if (quizDifficulty === "easy") {
                            const count = Math.min(
                              baseQuestions.length,
                              Math.max(
                                3,
                                Math.round(baseQuestions.length * 0.3)
                              )
                            );
                            viewQuestions = baseQuestions.slice(0, count);
                          } else if (quizDifficulty === "medium") {
                            const count = Math.min(
                              baseQuestions.length,
                              Math.max(
                                5,
                                Math.round(baseQuestions.length * 0.6)
                              )
                            );
                            viewQuestions = baseQuestions.slice(0, count);
                          }

                          return viewQuestions.map((q, idx) => {
                            const rawOpts = Array.isArray(q.options)
                              ? q.options
                              : [];
                            let options = rawOpts;
                            let correctIdx =
                              typeof q.answer_index === "number"
                                ? q.answer_index
                                : 0;
                            if (!options.length) {
                              const correctText =
                                q.answer ||
                                q.answer_text ||
                                q.correct ||
                                q.prompt ||
                                q.question ||
                                "Answer not available";
                              options = [
                                correctText,
                                "Incorrect / not related",
                                "Partially correct",
                                "Not mentioned in summary",
                              ];
                              correctIdx = 0;
                            }
                            const r = mapResult[q.id];
                            const chosen = quizAnswers[q.id];

                            return (
                              <div
                                key={q.id}
                                style={{
                                  background: "#ffffff",
                                  borderRadius: 10,
                                  padding: 10,
                                  border: "1px solid rgba(15,23,42,0.12)",
                                }}
                              >
                                <div
                                  style={{
                                    fontSize: 13,
                                    color: "#000000",
                                    marginBottom: 4,
                                  }}
                                >
                                  Q{idx + 1}
                                </div>
                                <div
                                  style={{
                                    fontSize: 14,
                                    color: "#000000",
                                    marginBottom: 4,
                                  }}
                                >
                                  {q.question}
                                </div>
                                {q.prompt && (
                                  <div
                                    style={{
                                      fontSize: 13,
                                      color: "#cfe8ff",
                                      marginBottom: 6,
                                    }}
                                  >
                                    {q.prompt}
                                  </div>
                                )}

                                <div
                                  style={{
                                    display: "flex",
                                    flexDirection: "column",
                                    gap: 6,
                                  }}
                                >
                                  {options.map((opt, oIdx) => {
                                    let borderColor =
                                      "rgba(255,255,255,0.06)";
                                    let bg = "#050a10";
                                    if (quizSubmitted) {
                                      if (oIdx === correctIdx) {
                                        borderColor = "#22c55e";      // lighter green
                                        bg = "#86efac";               // pale green background
                                      } else if (chosen === oIdx && chosen !== correctIdx) {
                                        borderColor = "#ef4444";      // lighter red
                                        bg = "#fca5a5";               // pale red background
                                      }
                                    } else if (chosen === oIdx) {
                                      borderColor = accent;
                                    }
                                    return (
                                      <label
                                        key={oIdx}
                                        style={{
                                          display: "flex",
                                          alignItems: "center",
                                          gap: 8,
                                          padding: "6px 8px",
                                          borderRadius: 8,
                                          border: `1px solid ${borderColor}`,
                                          background:
                                          quizSubmitted && (oIdx === correctIdx || chosen === oIdx)
                                            ? bg
                                            : "#4aa3ff",
                                          cursor: "pointer",
                                          fontSize: 13,
                                          color: "#000000",
                                        }}
                                      >
                                        <input
                                          type="radio"
                                          name={q.id}
                                          value={oIdx}
                                          checked={chosen === oIdx}
                                          onChange={() =>
                                            handleQuizOptionChange(
                                              q.id,
                                              oIdx
                                            )
                                          }
                                          style={{ margin: 0 }}
                                          disabled={quizSubmitted}
                                        />
                                        <span>{opt}</span>
                                      </label>
                                    );
                                  })}
                                </div>

                                {quizSubmitted && r && (
                                  <div
                                    style={{
                                      marginTop: 6,
                                      fontSize: 12,
                                      fontWeight: 600,
                                      color: r.isCorrect
                                        ? "#4ade80"
                                        : "#fca5a5",
                                    }}
                                  >
                                    {r.isCorrect
                                      ? "Correct"
                                      : "Wrong"}
                                  </div>
                                )}
                              </div>
                            );
                          });
                        })()}
                      </div>
                    )}
                </div>

                <div
                  style={{
                    marginTop: 10,
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <button
                    onClick={handleQuizSubmit}
                    className="btn btn-accent"
                    disabled={
                      !quiz ||
                      !quiz.questions ||
                      quiz.questions.length === 0 ||
                      quizSubmitted
                    }
                  >
                    Submit
                  </button>

                  {quizResult && (
                    <div
                      style={{ fontSize: 13, color: "#e6f6ff" }}
                    >
                      Score: <b>{quizResult.correct}</b> /{" "}
                      {quizResult.total} &nbsp;|&nbsp; Correct:{" "}
                      {quizResult.correct} &nbsp;|&nbsp; Wrong:{" "}
                      {quizResult.wrong}
                    </div>
                  )}
                </div>
              </motion.div>
            ) : focusPanel === "smart" ? (
              <motion.div
                className="glass"
                style={{
                  padding: 16,
                  maxHeight: "calc(100vh - 120px)",
                  display: "flex",
                  flexDirection: "column",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: 10,
                  }}
                >
                  <b style={{ color: gold }}>Smart Search</b>
                  <span style={{ fontSize: 13, color: "#9fbfe6" }}>
                    Ask questions from the summary
                  </span>
                </div>

                <div
                  style={{
                    flex: 1,
                    overflowY: "auto",
                    paddingRight: 6,
                    marginTop: 4,
                    marginBottom: 10,
                  }}
                  className="quiz-scroll"
                >
                  {smartMessages.length === 0 &&
                    !smartLoading &&
                    !smartError && (
                      <div style={{ fontSize: 13, color: "#9fbfe6" }}>
                        Ask something like: “What is the main idea of this chapter?”
                      </div>
                    )}

                  {smartMessages.length > 0 && (
                    <div
                      style={{
                        display: "flex",
                        flexDirection: "column",
                        gap: 8,
                      }}
                    >
                      {smartMessages.map((m, i) => {
                        const isUser = m.role === "user";
                        return (
                          <div
                            key={i}
                            style={{
                              display: "flex",
                              justifyContent: isUser
                                ? "flex-end"
                                : "flex-start",
                            }}
                          >
                            <div
                              style={{
                                maxWidth: "80%",
                                borderRadius: 12,
                                padding: 10,
                                fontSize: 13,
                                lineHeight: 1.5,
                                whiteSpace: "pre-wrap",
                                background: isUser
                                  ? "#4aa3ff"
                                  : "#ffffff",
                                color: isUser ? "#000000" : "#000000",
                                border: isUser
                                  ? "1px solid rgba(15,23,42,0.2)"
                                  : "1px solid rgba(15,23,42,0.12)",
                              }}
                            >
                              {m.text}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {smartError && (
                    <div
                      style={{
                        fontSize: 13,
                        color: "#ffb4b4",
                        marginTop: 8,
                      }}
                    >
                      {smartError}
                    </div>
                  )}
                </div>

                <div style={{ display: "flex", gap: 8 }}>
                  <input
                    type="text"
                    value={smartQuestion}
                    onChange={(e) => setSmartQuestion(e.target.value)}
                    placeholder="Type your question..."
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        handleSmartAsk();
                      }
                    }}
                    style={{
                      flex: 1,
                      padding: "6px 8px",
                      borderRadius: 8,
                      border: "1px solid rgba(148,163,184,0.6)",
                      fontSize: 13,
                      color: "#000000", // question text in black
                    }}
                  />
                  <button
                    onClick={handleSmartAsk}
                    disabled={smartLoading || !smartQuestion.trim()}
                    className="btn btn-accent"
                    style={{ whiteSpace: "nowrap" }}
                  >
                    {smartLoading ? "Asking..." : "Ask"}
                  </button>
                </div>
              </motion.div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}
