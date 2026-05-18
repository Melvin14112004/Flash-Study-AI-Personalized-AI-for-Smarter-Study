// src/utils/ttsApi.js
// Helper wrappers used by Hub.jsx for TTS generation + playback.
// Each function returns { ok: boolean, info?: any } and logs best-effort details.

export async function requestTTSFor(saveName, upload) {
  if (!saveName || !upload) return { ok: false, info: "missing args" };
  const id = upload.id || upload.pdf_id || null;
  if (!id) return { ok: false, info: "no id" };

  const variants = [
    `/save/${encodeURIComponent(saveName)}/${encodeURIComponent(id)}/tts`,
    `/api/upload/${encodeURIComponent(id)}/generate_tts?save_id=${encodeURIComponent(saveName)}`,
    `/api/save/${encodeURIComponent(saveName)}/upload/${encodeURIComponent(id)}/generate_tts`
  ];

  for (const p of variants) {
    try {
      const res = await fetch(p, { method: "POST" });
      const text = await res.text().catch(() => "");
      let body = null;
      try { body = text ? JSON.parse(text) : null; } catch (e) { body = null; }

      if (res.ok && (!body || body.status === "ok")) {
        return { ok: true, info: { endpoint: p, body } };
      }
      // server may respond 200 with body saying error
      if (res.ok && body) {
        return { ok: body.status === "ok", info: { endpoint: p, body } };
      }
      // otherwise keep trying
    } catch (err) {
      console.warn("requestTTSFor variant error", p, err);
    }
  }

  return { ok: false, info: "all variants failed" };
}

export async function playTTSFor(saveName, upload) {
  if (!saveName || !upload) return { ok: false, info: "missing args" };
  const id = upload.id || upload.pdf_id || null;
  if (!id) return { ok: false, info: "no id" };

  // 1) Try if upload record contains direct URL fields
  const directCandidates = [
    upload.tts_url, upload.ttsUrl, upload.tts, upload.tts_url_mp3, upload.ttsMp3, upload.audio_url
  ].filter(Boolean);

  for (const url of directCandidates) {
    try {
      const a = new Audio(url);
      await a.play().catch((e) => console.warn("direct audio play rejected", e));
      return { ok: true, info: { method: "direct", url } };
    } catch (err) {
      console.warn("direct audio candidate failed", url, err);
    }
  }

  // 2) Try serve endpoint that returns audio blob or url
  const serve = `/api/upload/${encodeURIComponent(id)}/tts?save_id=${encodeURIComponent(saveName)}`;
  try {
    const res = await fetch(serve, { method: "GET" });
    if (!res.ok) {
      const txt = await res.text().catch(() => "");
      console.warn("serve TTS non-ok:", res.status, txt);
    } else {
      const ct = res.headers.get("content-type") || "";
      if (ct.startsWith("audio/")) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = new Audio(url);
        await a.play().catch((e) => console.error("Playback error for served blob", e));
        return { ok: true, info: { method: "serve-blob", url } };
      }
      const text = await res.text().catch(() => "");
      let body = null;
      try { body = text ? JSON.parse(text) : null; } catch (e) { body = null; }
      if (body && (body.url || body.tts_url)) {
        const u = body.url || body.tts_url;
        const a = new Audio(u);
        await a.play();
        return { ok: true, info: { method: "serve-json-url", url: u } };
      }
      console.warn("serve TTS unknown payload:", text);
    }
  } catch (err) {
    console.warn("serve TTS request failed", err);
  }

  // 3) Fallback legacy variants (try GET endpoints returning audio or JSON with url)
  const fallbackVariants = [
    `/save/${encodeURIComponent(saveName)}/${encodeURIComponent(id)}/play_tts`,
    `/api/save/${encodeURIComponent(saveName)}/upload/${encodeURIComponent(id)}/play_tts`,
    `/api/upload/${encodeURIComponent(id)}/play_tts?save_id=${encodeURIComponent(saveName)}`,
    `/api/upload/${encodeURIComponent(id)}/tts?save_id=${encodeURIComponent(saveName)}`
  ];

  for (const p of fallbackVariants) {
    try {
      const res = await fetch(p, { method: "GET" });
      if (!res.ok) continue;
      const ct = res.headers.get("content-type") || "";
      if (ct.startsWith("audio/")) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = new Audio(url);
        await a.play();
        return { ok: true, info: { method: "fallback-blob", url, endpoint: p } };
      }
      const text = await res.text().catch(() => "");
      let body = null;
      try { body = text ? JSON.parse(text) : null; } catch (e) { body = null; }
      if (body && (body.url || body.tts_url)) {
        const u = body.url || body.tts_url;
        const a = new Audio(u);
        await a.play();
        return { ok: true, info: { method: "fallback-json-url", url: u, endpoint: p } };
      }
    } catch (err) {
      console.warn("fallback variant failed", p, err);
    }
  }

  return { ok: false, info: "no playable audio found" };
}
