import React, { useState } from "react";
import SaveManager from "../components/SaveManager";
import UploadPDF from "../components/UploadPDF";
import axios from "axios";

export default function Home(){
  const [saveId, setSaveId] = useState(localStorage.getItem("active_save") || "");
  const [summary, setSummary] = useState("");
  const [loading, setLoading] = useState(false);

  function onSaveSelected(id){
    setSaveId(id);
    localStorage.setItem("active_save", id);
  }

  // helper: fetch uploads for a save (latest first)
  async function fetchUploadsForSave(save) {
    if (!save) throw new Error("No save selected");
    const res = await axios.get(`/api/uploads?save_id=${encodeURIComponent(save)}`);
    return res.data.uploads || [];
  }

  async function doSummarize(){
    if(!saveId) return alert("choose save");
    setLoading(true);
    try {
      const uploads = await fetchUploadsForSave(saveId);
      if (!uploads.length) {
        alert("No uploads found for this save. Go to Dashboard and upload a PDF.");
        setLoading(false);
        return;
      }

      const latest = uploads[uploads.length - 1];
      const pdfId = latest.id || latest.pdf_id;
      if (!pdfId) {
        alert("Could not determine PDF id for summarization.");
        setLoading(false);
        return;
      }

      // trigger summarize
      await axios.post(`/api/save/${encodeURIComponent(saveId)}/${encodeURIComponent(pdfId)}/summarize`);

      // refetch uploads and pick the updated summary
      const updated = await fetchUploadsForSave(saveId);
      const updatedItem = updated.find((u) => (u.id || u.pdf_id) === pdfId);
      setSummary(updatedItem?.summary || "No summary available yet.");
    } catch (err) {
      console.error("Summarize error:", err);
      alert("Failed to summarize. See console for details.");
    } finally {
      setLoading(false);
    }
  }

  async function createFlashcards(){
    if(!saveId) return alert("choose save");
    setLoading(true);
    try {
      const uploads = await fetchUploadsForSave(saveId);
      if (!uploads.length) {
        alert("No uploads found for this save.");
        setLoading(false);
        return;
      }
      const pdfId = uploads[uploads.length - 1].id || uploads[uploads.length - 1].pdf_id;
      await axios.post(`/api/save/${encodeURIComponent(saveId)}/${encodeURIComponent(pdfId)}/flashcards`);
      alert("Flashcards requested. Check Dashboard or saves folder.");
    } catch (err) {
      console.error("Flashcards error:", err);
      alert("Failed to create flashcards.");
    } finally {
      setLoading(false);
    }
  }

  async function createQuiz(level = "easy"){
    if(!saveId) return alert("choose save");
    setLoading(true);
    try {
      const uploads = await fetchUploadsForSave(saveId);
      if (!uploads.length) {
        alert("No uploads found for this save.");
        setLoading(false);
        return;
      }
      const pdfId = uploads[uploads.length - 1].id || uploads[uploads.length - 1].pdf_id;
      await axios.post(`/api/save/${encodeURIComponent(saveId)}/${encodeURIComponent(pdfId)}/quiz`, { level });
      alert("Quiz generation requested.");
    } catch (err) {
      console.error("Quiz error:", err);
      alert("Failed to generate quiz.");
    } finally {
      setLoading(false);
    }
  }

  async function playAudioSummary(){
    if(!saveId) return alert("choose save");
    setLoading(true);
    try {
      const uploads = await fetchUploadsForSave(saveId);
      if (!uploads.length) {
        alert("No uploads found for this save.");
        setLoading(false);
        return;
      }
      const pdfId = uploads[uploads.length - 1].id || uploads[uploads.length - 1].pdf_id;

      const r = await axios.post(`/api/save/${encodeURIComponent(saveId)}/${encodeURIComponent(pdfId)}/tts`, { text: summary || "" });
      const j = r.data || {};

      // backend may return different keys: try common variants
      const file = j.audio_file || j.tts_file || j.file || j.path;
      let audioUrl = null;

      if (file) {
        // if the backend returned a full URL or path, use it
        if (file.startsWith("http") || file.startsWith("/")) {
          audioUrl = file;
        } else {
          // construct likely static serving path
          audioUrl = `/saves/${encodeURIComponent(saveId)}/tts/${encodeURIComponent(file)}`;
        }
      } else if (j.url) {
        audioUrl = j.url;
      }

      if (!audioUrl) {
        alert("TTS generated but no audio URL returned by server.");
        setLoading(false);
        return;
      }

      window.open(audioUrl, "_blank");
    } catch (err) {
      console.error("TTS error:", err);
      alert("Failed to generate/play audio.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{padding:20}}>
      <h2>Flash Study AI — Home</h2>
      <SaveManager onSaveSelected={onSaveSelected} />
      {saveId && <>
        <UploadPDF saveName={saveId} onUploaded={()=>console.log("uploaded")} />
        <div style={{marginTop:12}}>
          <button onClick={doSummarize} disabled={loading}>{loading ? "Working..." : "Summarize"}</button>
          <button onClick={createFlashcards} disabled={loading}>Create Flashcards</button>
          <button onClick={() => createQuiz("easy")} disabled={loading}>Generate Quiz</button>
          <button onClick={playAudioSummary} disabled={loading}>Audio Summary</button>
        </div>
        <div style={{marginTop:12}}>
          <h4>Summary</h4>
          <div style={{whiteSpace:"pre-wrap"}}>{summary}</div>
        </div>
      </>}
    </div>
  );
}
