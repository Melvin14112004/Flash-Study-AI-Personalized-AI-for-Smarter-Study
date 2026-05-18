// src/components/SaveManager.jsx
import React, { useEffect, useState } from "react";
import axios from "axios";

const API_BASE = "http://127.0.0.1:5000"; // ensure correct backend URL

export default function SaveManager({ onSaveSelected }) {
  const [saves, setSaves] = useState([]);
  const [newName, setNewName] = useState("");

  useEffect(() => {
    load();
  }, []);

  async function load() {
    try {
      const res = await axios.get(`${API_BASE}/api/saves`);
      setSaves(res.data.saves || []);
    } catch (err) {
      console.error("Failed to load saves:", err);
      setSaves([]);
    }
  }

  async function createSave() {
    try {
      const payload = { save_name: newName || undefined };
      const res = await axios.post(`${API_BASE}/api/save`, payload);
      const id = res.data.save;
      alert(`✅ Save created: ${id}`);
      onSaveSelected(id);
      load();
    } catch (err) {
      console.error("Save creation failed:", err);
      alert("❌ Failed to create save. Check backend connection.");
    }
  }

  function continueSave(id) {
    onSaveSelected(id);
  }

  return (
    <div style={{ padding: 20, border: "1px solid #ddd", borderRadius: 8 }}>
      <h3>Save Manager</h3>
      <div>
        <input
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="new save name (optional)"
        />
        <button onClick={createSave}>New Save</button>
      </div>
      <hr />
      <h4>Continue existing</h4>
      <ul>
        {saves.map((s) => (
          <li key={s}>
            {s} <button onClick={() => continueSave(s)}>Continue</button>
          </li>
        ))}
      </ul>
    </div>
  );
}
