import os, json, random, math

try:
    import PyPDF2
except Exception:
    PyPDF2 = None


def _read_summary(save_path, upload_id):
    meta_path = os.path.join(save_path, "meta.json")
    if not os.path.exists(meta_path):
        return None
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        for arr in ("pdfs", "uploads"):
            for e in meta.get(arr, []):
                if e.get("id") == upload_id:
                    return e.get("summary") or e.get("short") or ""
    except Exception:
        pass
    return None


def _extract_text(pdf_path):
    if PyPDF2 is None or not pdf_path:
        return ""
    try:
        text = []
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for p in reader.pages:
                t = p.extract_text() or ""
                text.append(t.replace("\r", " "))
        return "\n".join(text)
    except Exception:
        return ""


def _sentences(text):
    import re
    s = re.split(r'(?<=[.!?])\s+', text.strip())
    s = [x.strip() for x in s if x.strip()]
    return s


def _short_phrase(s, max_words=14):
    words = s.replace("\n", " ").split()
    if len(words) <= max_words:
        return " ".join(words).strip()
    return " ".join(words[:max_words]).strip() + "..."


def _generic_distractors():
    return [
        "It mainly focuses on memorising isolated rules.",
        "It is only about writing and spelling accuracy.",
        "It deals with topics unrelated to language learning.",
        "It is described as an advanced research activity.",
    ]


def _extract_concepts(sentences):
    """
    Try to pull (subject, description) concept pairs from sentences.
    More flexible than the old version, so it works on more academic summaries.
    """
    import re
    concepts = []

    patterns = [
        r"^(?P<subj>.+?)\s+is\s+(?P<desc>.+)$",
        r"^(?P<subj>.+?)\s+are[:\s]+(?P<desc>.+)$",
        r"^(?P<subj>.+?)\s+involves\s+(?P<desc>.+)$",
        r"^(?P<subj>.+?)\s+focus(?:es)?\s+on\s+(?P<desc>.+)$",
        r"^(?P<subj>.+?)\s+examines\s+(?P<desc>.+)$",
        r"^(?P<subj>.+?)\s+discuss(?:es|ing)?\s+(?P<desc>.+)$",
        r"^(?P<subj>.+?)\s+highlights\s+(?P<desc>.+)$",
        r"^(?P<subj>.+?)\s+explores\s+(?P<desc>.+)$",
        r"^(?P<subj>.+?)\s+relates\s+to\s+(?P<desc>.+)$",
    ]

    for s in sentences:
        s = s.strip()
        if len(s) < 30:
            continue

        for pat in patterns:
            m = re.search(pat, s, flags=re.IGNORECASE)
            if not m:
                continue

            subj = m.group("subj").strip().rstrip(",:;.")
            desc = m.group("desc").strip()

            # avoid insane subjects
            if len(subj.split()) > 14:
                continue

            answer_phrase = _short_phrase(desc, 18)
            concepts.append({
                "subject": subj,
                "sentence": s,
                "answer": answer_phrase,
            })
            break

    return concepts


def _pick_for_difficulty(concepts, difficulty):
    n = len(concepts)
    if n == 0:
        return []

    if difficulty == "easy":
        base = max(3, min(6, n // 2 + 1))
        idxs = list(range(0, n, 3))
    elif difficulty == "medium":
        base = max(4, min(8, int(0.7 * n)))
        idxs = list(range(1, n, 3))
    else:
        base = max(5, min(10, n))
        idxs = list(range(2, n, 3))

    picked = [concepts[i] for i in idxs if i < n]
    if len(picked) < base:
        need = base - len(picked)
        extra = [c for c in concepts if c not in picked]
        random.shuffle(extra)
        picked.extend(extra[:need])
    return picked[:base]


def _build_question(concept, difficulty, rng, all_answers):
    subj = concept["subject"]
    correct = concept["answer"]

    # pick a question type based on difficulty
    if difficulty == "easy":
        q_types = ["best_answer", "true_false"]
    elif difficulty == "medium":
        q_types = ["best_answer", "best_statement", "true_false"]
    else:  # hard
        q_types = ["best_statement", "best_answer", "true_false"]

    q_type = rng.choice(q_types)

    # ---------- build base candidate answers for MCQ ----------
    candidates = [a for a in all_answers if a != correct]
    rng.shuffle(candidates)
    distractors = []

    for c in candidates:
        if c.lower() == correct.lower():
            continue
        if any(c.lower() in d.lower() or d.lower() in c.lower() for d in distractors):
            continue
        distractors.append(c)
        if len(distractors) == 2:
            break

    gen_d = _generic_distractors()
    rng.shuffle(gen_d)
    for g in gen_d:
        if len(distractors) >= 3:
            break
        if g.lower() == correct.lower():
            continue
        distractors.append(g)

    # ---------- TYPE 1: choose the best answer ----------
    if q_type == "best_answer":
        qtext = f"What does {subj} mainly refer to in the summary?"
        options = [correct] + distractors[:3]
        rng.shuffle(options)
        answer_index = options.index(correct)

    # ---------- TYPE 2: choose the best statement ----------
    elif q_type == "best_statement":
        correct_stmt = f"{subj} mainly relates to {correct}"

        wrong_stmts = []
        for d in distractors:
            wrong_stmts.append(f"{subj} mainly relates to {d}")
            if len(wrong_stmts) == 3:
                break

        while len(wrong_stmts) < 3:
            wrong_stmts.append(f"{subj} is not discussed in the summary.")

        options = [correct_stmt] + wrong_stmts[:3]
        rng.shuffle(options)
        answer_index = options.index(correct_stmt)

        qtext = f"Which statement about {subj} is correct according to the summary?"

    # ---------- TYPE 3: True / False ----------
    else:  # true_false
        make_true = rng.choice([True, False])

        if make_true:
            stmt = f"In the summary, {subj} is related to {correct}."
            answer_index = 0  # True
        else:
            wrong = distractors[0] if distractors else "something unrelated."
            stmt = f"In the summary, {subj} is related to {wrong}."
            answer_index = 1  # False

        qtext = f"True or False: {stmt}"
        options = ["True", "False"]

    return {
        "question": qtext,
        "options": options,
        "answer_index": answer_index,
        "type": q_type,
    }


def generate_quiz(pdf_path, save_path=None, upload_id=None, difficulty="easy"):
    text = ""
    if save_path and upload_id:
        text = _read_summary(save_path, upload_id) or ""
    if not text:
        text = _extract_text(pdf_path) or ""

    sentences = _sentences(text)
    concepts = _extract_concepts(sentences)

    base = save_path or "."
    os.makedirs(os.path.join(base, "quiz"), exist_ok=True)
    out_file = os.path.join(base, "quiz", f"{upload_id or 'quiz'}.json")

    # ---------- normal path: concept-based questions ----------
    if concepts:
        concepts.sort(key=lambda c: len(c["sentence"]))
        rng = random.Random(f"mcq-v3-{difficulty}-{upload_id}")
        picked = _pick_for_difficulty(concepts, difficulty)
        all_answers = [c["answer"] for c in concepts]

        questions = []
        for idx, c in enumerate(picked):
            q = _build_question(c, difficulty, rng, all_answers)
            q["id"] = f"q{idx+1}"
            questions.append(q)

        quiz = {"difficulty": difficulty, "questions": questions}
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(quiz, f, indent=2)
        return {"questions": len(questions), "path": out_file}

    # ---------- fallback path: no concepts → sentence-based MCQs ----------
    clean_sents = [s for s in sentences if len(s.strip()) > 40]
    clean_sents = clean_sents[:12]
    if len(clean_sents) < 2:
        quiz = {"difficulty": difficulty, "questions": []}
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(quiz, f, indent=2)
        return {"questions": 0, "path": out_file}

    rng = random.Random(f"fallback-{difficulty}-{upload_id}")
    snippets = [_short_phrase(s, 18) for s in clean_sents]

    n = len(clean_sents)
    if difficulty == "easy":
        q_target = min(4, n)
    elif difficulty == "medium":
        q_target = min(6, n)
    else:
        q_target = min(8, n)

    idxs = list(range(n))
    rng.shuffle(idxs)
    idxs = idxs[:q_target]

    questions = []
    for qi, si in enumerate(idxs, start=1):
        correct = snippets[si]
        others = [snippets[j] for j in range(n) if j != si]
        rng.shuffle(others)
        opts = [correct] + others[:3]
        rng.shuffle(opts)

        qtext = "Choose the option that best represents an important idea from the summary."

        questions.append({
            "id": f"q{qi}",
            "question": qtext,
            "options": opts,
            "answer_index": opts.index(correct),
            "type": "fallback_best_sentence",
        })

    quiz = {"difficulty": difficulty, "questions": questions}
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(quiz, f, indent=2)
    return {"questions": len(questions), "path": out_file}
