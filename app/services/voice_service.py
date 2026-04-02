"""
AI Voice Prescription Service — Speech-to-Text + RapidFuzz Medicine Correction
================================================================================
This module provides:
  1. Speech-to-text transcription using Faster-Whisper (if available)
  2. RapidFuzz-powered medicine name correction engine
  3. Multi-suggestion system for ambiguous medicine names
  4. Intelligent medicine extraction & parsing from transcribed text
"""

import os
import re
import logging
import tempfile
from time import perf_counter

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
#  RAPIDFUZZ MEDICINE CORRECTION ENGINE
# ══════════════════════════════════════════════════════════════════════════════

try:
    from rapidfuzz import fuzz, process as rfprocess
    RAPIDFUZZ_AVAILABLE = True
    logger.info("[VOICE] RapidFuzz loaded successfully — high-accuracy medicine matching enabled")
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    logger.warning("[VOICE] RapidFuzz not installed. Using fallback matching. Run: pip install rapidfuzz")


# ══════════════════════════════════════════════════════════════════════════════
#  WHISPER MODEL (Lazy-loaded singleton)
# ══════════════════════════════════════════════════════════════════════════════

_whisper_model = None


def _get_whisper_model():
    """Lazy-load the Faster-Whisper model (downloads on first use)."""
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model

    try:
        from faster_whisper import WhisperModel
    except ImportError as ie:
        import sys
        logger.error(f"[WHISPER] Import failed: {ie}. Python: {sys.executable}")
        raise RuntimeError(
            f"faster-whisper import failed: {ie}. "
            f"Python={sys.executable}. "
            f"Run: {sys.executable} -m pip install faster-whisper"
        )

    try:
        model_size = os.getenv("WHISPER_MODEL_SIZE", "tiny.en")
        device = os.getenv("WHISPER_DEVICE", "cpu")
        compute_type = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

        logger.info(f"[WHISPER] Loading model '{model_size}' on {device} ({compute_type})...")
        _whisper_model = WhisperModel(model_size, device=device, compute_type=compute_type)
        logger.info("[WHISPER] Model loaded successfully.")
        return _whisper_model
    except Exception as e:
        logger.error(f"[WHISPER] Failed to load model: {e}")
        raise


def warmup_whisper_model():
    """Load Whisper model in background during app startup."""
    try:
        _get_whisper_model()
        logger.info("[WHISPER] Warmup complete.")
    except Exception as e:
        logger.warning(f"[WHISPER] Warmup skipped: {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  TRANSCRIPTION
# ══════════════════════════════════════════════════════════════════════════════

def transcribe_audio(audio_file_path: str) -> dict:
    """
    Transcribe an audio file using Faster-Whisper.

    Args:
        audio_file_path: Path to the audio file (WAV, WebM, MP3, etc.)

    Returns:
        dict with keys: text, segments, language, duration
    """
    model = _get_whisper_model()

    try:
        t0 = perf_counter()
        beam_size = int(os.getenv("WHISPER_BEAM_SIZE", "1"))
        best_of = int(os.getenv("WHISPER_BEST_OF", "1"))
        language = os.getenv("WHISPER_LANGUAGE", "en")
        vad_filter = os.getenv("WHISPER_VAD_FILTER", "false").lower() in ("1", "true", "yes", "on")
        min_silence_ms = int(os.getenv("WHISPER_MIN_SILENCE_MS", "450"))
        speech_pad_ms = int(os.getenv("WHISPER_SPEECH_PAD_MS", "220"))
        temperature = float(os.getenv("WHISPER_TEMPERATURE", "0"))

        segments, info = model.transcribe(
            audio_file_path,
            beam_size=beam_size,
            best_of=best_of,
            language=language,
            temperature=temperature,
            condition_on_previous_text=False,
            vad_filter=vad_filter,
            vad_parameters=dict(
                min_silence_duration_ms=min_silence_ms,
                speech_pad_ms=speech_pad_ms,
            ),
        )

        segment_list = []
        full_text_parts = []

        for segment in segments:
            segment_list.append({
                "start": round(segment.start, 2),
                "end": round(segment.end, 2),
                "text": segment.text.strip(),
            })
            full_text_parts.append(segment.text.strip())

        full_text = " ".join(full_text_parts).strip()

        elapsed = perf_counter() - t0
        logger.info(
            f"[WHISPER] Transcribed {info.duration:.1f}s audio in {elapsed:.2f}s "
            f"(beam={beam_size}, model={os.getenv('WHISPER_MODEL_SIZE', 'tiny.en')}) "
            f"-> \"{full_text[:80]}...\""
        )

        return {
            "success": True,
            "text": full_text,
            "segments": segment_list,
            "language": info.language,
            "language_probability": round(info.language_probability, 3),
            "duration": round(info.duration, 2),
        }
    except Exception as e:
        logger.error(f"[WHISPER] Transcription failed: {e}")
        return {
            "success": False,
            "text": "",
            "error": str(e),
        }


def save_uploaded_audio(audio_file) -> str:
    """
    Save an uploaded audio file to a temporary location.

    Args:
        audio_file: Flask FileStorage object

    Returns:
        Path to saved temporary file
    """
    original_name = audio_file.filename or "recording.webm"
    ext = os.path.splitext(original_name)[1] or ".webm"

    fd, temp_path = tempfile.mkstemp(suffix=ext, prefix="whisper_")
    os.close(fd)

    audio_file.save(temp_path)
    logger.info(f"[WHISPER] Saved uploaded audio to {temp_path} ({os.path.getsize(temp_path)} bytes)")

    return temp_path


# ══════════════════════════════════════════════════════════════════════════════
#  MEDICINE KNOWLEDGE BASE
# ══════════════════════════════════════════════════════════════════════════════

KNOWN_MEDICINES = [
    # ─── Analgesics / Antipyretics ───
    "Paracetamol", "Acetaminophen", "Ibuprofen", "Aspirin", "Diclofenac",
    "Naproxen", "Mefenamic Acid", "Piroxicam", "Aceclofenac", "Nimesulide",
    "Tramadol", "Ketorolac", "Indomethacin", "Etoricoxib", "Celecoxib",
    # ─── Popular Indian Brands ───
    "Dolo", "Crocin", "Combiflam", "Saridon", "Voveran", "Flexon",
    "Calpol", "Meftal", "Zerodol", "Hifenac",
    # ─── Antibiotics ───
    "Amoxicillin", "Azithromycin", "Ciprofloxacin", "Doxycycline", "Metronidazole",
    "Cephalexin", "Cefixime", "Ceftriaxone", "Levofloxacin", "Clindamycin",
    "Erythromycin", "Clarithromycin", "Amoxyclav", "Ampicillin", "Penicillin",
    "Ofloxacin", "Norfloxacin", "Cefuroxime", "Cefpodoxime", "Linezolid",
    "Cotrimoxazole", "Nitrofurantoin", "Gentamicin", "Vancomycin", "Meropenem",
    "Tetracycline", "Rifampicin", "Isoniazid", "Pyrazinamide", "Ethambutol",
    "Augmentin", "Zithromax", "Monocef",
    # ─── Antifungals ───
    "Fluconazole", "Itraconazole", "Ketoconazole", "Clotrimazole", "Terbinafine",
    # ─── Antivirals ───
    "Acyclovir", "Oseltamivir", "Remdesivir", "Favipiravir", "Valacyclovir",
    # ─── Antihistamines ───
    "Cetirizine", "Levocetirizine", "Loratadine", "Fexofenadine", "Chlorpheniramine",
    "Desloratadine", "Hydroxyzine", "Promethazine", "Diphenhydramine",
    "Allegra", "Zyrtec",
    # ─── Antacids / GI ───
    "Omeprazole", "Pantoprazole", "Ranitidine", "Famotidine", "Esomeprazole",
    "Rabeprazole", "Lansoprazole", "Domperidone", "Ondansetron", "Sucralfate",
    "Metoclopramide", "Drotaverine", "Dicyclomine", "Loperamide", "Bisacodyl",
    "Lactulose", "Aluminium Hydroxide", "Magnesium Hydroxide", "Antacid Gel",
    "Pan D", "Rantac", "Gelusil",
    # ─── Antidiabetics ───
    "Metformin", "Glimepiride", "Glipizide", "Gliclazide", "Sitagliptin",
    "Vildagliptin", "Empagliflozin", "Dapagliflozin", "Pioglitazone",
    "Insulin Glargine", "Insulin Lispro", "Insulin Aspart",
    "Glycomet", "Januvia",
    # ─── Cardiovascular ───
    "Amlodipine", "Atenolol", "Metoprolol", "Losartan", "Telmisartan",
    "Ramipril", "Enalapril", "Valsartan", "Olmesartan", "Nifedipine",
    "Diltiazem", "Verapamil", "Clopidogrel", "Warfarin", "Enoxaparin",
    "Atorvastatin", "Rosuvastatin", "Simvastatin", "Fenofibrate", "Digoxin",
    "Furosemide", "Hydrochlorothiazide", "Spironolactone", "Torsemide",
    "Nitroglycerin", "Isosorbide Dinitrate", "Isosorbide Mononitrate",
    "Ecosprin", "Concor",
    # ─── Respiratory ───
    "Salbutamol", "Montelukast", "Theophylline", "Budesonide", "Fluticasone",
    "Ipratropium", "Tiotropium", "Formoterol", "Salmeterol", "Dextromethorphan",
    "Ambroxol", "Acetylcysteine", "Guaifenesin", "Codeine",
    "Asthalin", "Montair",
    # ─── CNS / Psychiatric ───
    "Alprazolam", "Diazepam", "Clonazepam", "Lorazepam", "Zolpidem",
    "Sertraline", "Fluoxetine", "Escitalopram", "Paroxetine", "Amitriptyline",
    "Duloxetine", "Venlafaxine", "Olanzapine", "Risperidone", "Quetiapine",
    "Haloperidol", "Lithium", "Carbamazepine", "Valproate", "Phenytoin",
    "Levetiracetam", "Gabapentin", "Pregabalin", "Donepezil",
    # ─── Steroids ───
    "Prednisolone", "Prednisone", "Dexamethasone", "Methylprednisolone",
    "Hydrocortisone", "Betamethasone", "Deflazacort",
    # ─── Vitamins & Supplements ───
    "Vitamin C", "Vitamin D3", "Vitamin B12", "Vitamin B Complex",
    "Folic Acid", "Iron", "Ferrous Sulphate", "Calcium",
    "Calcium Carbonate", "Zinc", "Multivitamin", "Omega 3",
    "Becosules", "Shelcal", "Limcee",
    # ─── Thyroid ───
    "Levothyroxine", "Thyroxine", "Carbimazole", "Propylthiouracil",
    "Thyronorm", "Eltroxin",
    # ─── Others ───
    "Methotrexate", "Hydroxychloroquine", "Colchicine", "Allopurinol",
    "Sildenafil", "Tadalafil", "Tamsulosin", "Finasteride",
    "Misoprostol", "Mifepristone", "Progesterone",
    "Cough Syrup", "ORS",
    # ─── Additional commonly confused medicines ───
    "Paracip", "Paradol", "Pacimol", "Metacin", "Dolopar",
]

# Common speech-recognition misheard → correct medicine mapping
SPEECH_CORRECTIONS = {
    "parasitamol": "Paracetamol",
    "paracitmol": "Paracetamol",
    "paracetamall": "Paracetamol",
    "parasitamall": "Paracetamol",
    "paracetmol": "Paracetamol",
    "paracitamol": "Paracetamol",
    "paracetemol": "Paracetamol",
    "paracetemall": "Paracetamol",
    "amoxicilin": "Amoxicillin",
    "amoxycillin": "Amoxicillin",
    "amoxiciline": "Amoxicillin",
    "amoxacilin": "Amoxicillin",
    "ibuprofin": "Ibuprofen",
    "ibuprofen": "Ibuprofen",
    "ibuprophen": "Ibuprofen",
    "ceptirizine": "Cetirizine",
    "cetirizin": "Cetirizine",
    "cetrizine": "Cetirizine",
    "cetrizin": "Cetirizine",
    "setirizine": "Cetirizine",
    "azithromicin": "Azithromycin",
    "azithromysin": "Azithromycin",
    "azithromycine": "Azithromycin",
    "pantoprazol": "Pantoprazole",
    "pantaprazole": "Pantoprazole",
    "pantoprazol": "Pantoprazole",
    "metformine": "Metformin",
    "metforman": "Metformin",
    "aspirine": "Aspirin",
    "atorvastatin": "Atorvastatin",
    "atorvastatine": "Atorvastatin",
    "ciproflaxacin": "Ciprofloxacin",
    "ciprofloxasin": "Ciprofloxacin",
    "omeprazol": "Omeprazole",
    "omeprezole": "Omeprazole",
    "amlodepine": "Amlodipine",
    "amlodipin": "Amlodipine",
    "losartane": "Losartan",
    "telmisartane": "Telmisartan",
    "montelukaste": "Montelukast",
    "monteleukast": "Montelukast",
    "prednisolone": "Prednisolone",
    "prednisalone": "Prednisolone",
    "salbutamole": "Salbutamol",
    "salbutamall": "Salbutamol",
    "levothyroxin": "Levothyroxine",
    "levothyroxene": "Levothyroxine",
}


# ══════════════════════════════════════════════════════════════════════════════
#  RAPIDFUZZ CORRECTION ENGINE
# ══════════════════════════════════════════════════════════════════════════════

def _get_all_medicines(db_medicines: list = None) -> list:
    """Merge known medicines with database medicines, deduplicated."""
    all_meds = list(KNOWN_MEDICINES)
    if db_medicines:
        existing_lower = {m.lower() for m in all_meds}
        for m in db_medicines:
            if m and m.lower() not in existing_lower:
                all_meds.append(m)
                existing_lower.add(m.lower())
    return all_meds


def correct_medicine_name(spoken: str, db_medicines: list = None) -> dict:
    """
    Correct a potentially misspelled medicine name using RapidFuzz.

    Algorithm:
      1. Check direct speech-correction lookup table
      2. Exact match (case-insensitive) against medicine database
      3. RapidFuzz fuzzy matching with >80% threshold
      4. Return best match or original text

    Args:
        spoken: The recognized/spoken medicine name
        db_medicines: Optional list of medicines from database

    Returns:
        dict with keys: name, corrected, confidence, suggestions
    """
    spoken_clean = spoken.strip()
    if not spoken_clean or len(spoken_clean) < 2:
        return {"name": spoken, "corrected": False, "confidence": "none", "suggestions": []}

    spoken_lower = spoken_clean.lower()

    # Step 1: Direct speech-correction lookup
    if spoken_lower in SPEECH_CORRECTIONS:
        corrected_name = SPEECH_CORRECTIONS[spoken_lower]
        logger.info(f"[MEDICINE-FIX] Direct correction: '{spoken}' → '{corrected_name}'")
        return {
            "name": corrected_name,
            "corrected": True,
            "confidence": "exact",
            "suggestions": [corrected_name],
        }

    all_medicines = _get_all_medicines(db_medicines)

    # Step 2: Exact case-insensitive match
    for med in all_medicines:
        if spoken_lower == med.lower():
            return {
                "name": med,
                "corrected": False,
                "confidence": "exact",
                "suggestions": [med],
            }

    # Step 3: RapidFuzz fuzzy matching
    if RAPIDFUZZ_AVAILABLE:
        return _rapidfuzz_match(spoken_clean, spoken_lower, all_medicines)
    else:
        return _fallback_match(spoken_clean, spoken_lower, all_medicines)


def _rapidfuzz_match(spoken: str, spoken_lower: str, all_medicines: list) -> dict:
    """Use RapidFuzz for high-quality fuzzy medicine matching."""
    # Use multiple scoring strategies for robustness
    # weighted_ratio gives a good balance for medicine names
    results = rfprocess.extract(
        spoken_lower,
        [m.lower() for m in all_medicines],
        scorer=fuzz.WRatio,
        limit=5,
        score_cutoff=60,   # Wider net, we'll filter later
    )

    if not results:
        capitalized = " ".join(w.capitalize() for w in spoken.split())
        return {
            "name": capitalized,
            "corrected": False,
            "confidence": "unknown",
            "suggestions": [],
        }

    # Map lowercase results back to original casing
    lower_to_original = {}
    for med in all_medicines:
        lower_to_original[med.lower()] = med

    suggestions = []
    for match_text, score, _idx in results:
        original_name = lower_to_original.get(match_text, match_text)
        suggestions.append({
            "name": original_name,
            "score": round(score, 1),
        })

    best = results[0]
    best_name = lower_to_original.get(best[0], best[0])
    best_score = best[1]

    # Determine confidence level and whether to auto-correct
    if best_score >= 95:
        confidence = "exact"
        corrected = spoken_lower != best[0]
    elif best_score >= 85:
        confidence = "high"
        corrected = True
    elif best_score >= 75:
        confidence = "medium"
        corrected = True
    else:
        confidence = "low"
        corrected = False
        # Don't auto-correct low confidence — return as-is
        capitalized = " ".join(w.capitalize() for w in spoken.split())
        return {
            "name": capitalized,
            "corrected": False,
            "confidence": "low",
            "suggestions": [s for s in suggestions if s["score"] >= 65],
        }

    # Auto-correct if score >= 75% (high/medium confidence)
    logger.info(
        f"[MEDICINE-FIX] RapidFuzz: '{spoken}' → '{best_name}' "
        f"(score={best_score:.1f}, confidence={confidence})"
    )

    return {
        "name": best_name,
        "corrected": corrected,
        "confidence": confidence,
        "suggestions": [s for s in suggestions if s["score"] >= 65],
    }


def _fallback_match(spoken: str, spoken_lower: str, all_medicines: list) -> dict:
    """Fallback Levenshtein-based matching when RapidFuzz is not available."""
    best_match = None
    best_score = float('inf')

    for med in all_medicines:
        med_lower = med.lower()

        if spoken_lower == med_lower:
            return {"name": med, "corrected": False, "confidence": "exact", "suggestions": []}

        dist = _levenshtein(spoken_lower, med_lower)
        if dist < best_score:
            best_score = dist
            best_match = med

    threshold = max(2, int(len(spoken_lower) * 0.4))

    if best_match and best_score <= threshold:
        return {
            "name": best_match,
            "corrected": best_score > 0,
            "confidence": "exact" if best_score == 0 else "high" if best_score <= 1 else "medium",
            "suggestions": [{"name": best_match, "score": 100 - best_score * 10}],
        }

    capitalized = " ".join(w.capitalize() for w in spoken.split())
    return {"name": capitalized, "corrected": False, "confidence": "unknown", "suggestions": []}


def _levenshtein(a: str, b: str) -> int:
    """Compute Levenshtein (edit) distance between two strings."""
    la, lb = len(a), len(b)
    if la == 0: return lb
    if lb == 0: return la

    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        curr = [i] + [0] * lb
        for j in range(1, lb + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            curr[j] = min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
        prev = curr
    return prev[lb]


def get_medicine_suggestions(spoken: str, db_medicines: list = None, limit: int = 5) -> list:
    """
    Get multiple medicine suggestions for a spoken word.
    Used for the suggestion popup when correction is ambiguous.

    Args:
        spoken: The spoken/recognized word
        db_medicines: Optional database medicines
        limit: Max number of suggestions

    Returns:
        List of dicts with name and score
    """
    spoken_clean = spoken.strip()
    if not spoken_clean or len(spoken_clean) < 2:
        return []

    all_medicines = _get_all_medicines(db_medicines)

    if RAPIDFUZZ_AVAILABLE:
        results = rfprocess.extract(
            spoken_clean.lower(),
            [m.lower() for m in all_medicines],
            scorer=fuzz.WRatio,
            limit=limit,
            score_cutoff=55,
        )

        lower_to_original = {m.lower(): m for m in all_medicines}
        return [
            {"name": lower_to_original.get(r[0], r[0]), "score": round(r[1], 1)}
            for r in results
        ]
    else:
        # Fallback: return top matches by Levenshtein distance
        scored = []
        spoken_lower = spoken_clean.lower()
        for med in all_medicines:
            dist = _levenshtein(spoken_lower, med.lower())
            if dist <= max(3, len(spoken_lower) // 2):
                score = max(0, 100 - dist * 15)
                scored.append({"name": med, "score": score})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:limit]


def correct_full_text(text: str, db_medicines: list = None) -> dict:
    """
    Correct medicine names in a full transcribed sentence.

    Algorithm:
      1. Convert text to lowercase
      2. Split into words
      3. Compare each word against medicine database
      4. If similarity > 80%, replace with correct name
      5. Keep other words unchanged

    Args:
        text: Full transcribed text (e.g., "parasitamol 500 mg twice daily")
        db_medicines: Optional database medicines

    Returns:
        dict with corrected_text, corrections list, and original text
    """
    if not text or not text.strip():
        return {"corrected_text": text, "corrections": [], "original": text}

    words = text.strip().split()
    corrections = []
    corrected_words = []

    # Noise words to skip
    SKIP_WORDS = {
        'mg', 'ml', 'g', 'mcg', 'iu', 'tablet', 'tablets', 'capsule', 'capsules',
        'drop', 'drops', 'unit', 'units', 'once', 'twice', 'thrice', 'daily',
        'after', 'before', 'with', 'food', 'meal', 'eating', 'empty', 'stomach',
        'take', 'prescribe', 'give', 'medicine', 'dose', 'dosage', 'frequency',
        'duration', 'instruction', 'for', 'days', 'weeks', 'months', 'times',
        'a', 'an', 'the', 'and', 'or', 'at', 'on', 'in', 'to', 'of',
        'night', 'bedtime', 'morning', 'evening', 'afternoon',
        'bd', 'tid', 'qid', 'od', 'sos', 'hs', 'prn',
        'next', 'med', 'then',
    }

    for word in words:
        word_clean = word.strip().rstrip('.,;:')
        word_lower = word_clean.lower()

        # Skip numbers, very short words, or known non-medicine words
        if (len(word_clean) < 3 or
                word_lower in SKIP_WORDS or
                re.match(r'^\d+$', word_clean)):
            corrected_words.append(word)
            continue

        result = correct_medicine_name(word_clean, db_medicines)

        if result["corrected"] and result["confidence"] in ("exact", "high", "medium"):
            corrections.append({
                "original": word_clean,
                "corrected": result["name"],
                "confidence": result["confidence"],
                "suggestions": result.get("suggestions", []),
            })
            # Replace preserving trailing punctuation
            trailing = word[len(word_clean):] if len(word) > len(word_clean) else ""
            corrected_words.append(result["name"] + trailing)
        else:
            corrected_words.append(word)

    corrected_text = " ".join(corrected_words)

    if corrections:
        logger.info(
            f"[MEDICINE-FIX] Corrected {len(corrections)} word(s): "
            + ", ".join(f"'{c['original']}' → '{c['corrected']}'" for c in corrections)
        )

    return {
        "corrected_text": corrected_text,
        "corrections": corrections,
        "original": text.strip(),
    }


# ══════════════════════════════════════════════════════════════════════════════
#  MEDICINE EXTRACTION / PARSING
# ══════════════════════════════════════════════════════════════════════════════

def _parse_frequency(text: str) -> str:
    """Extract medical frequency code from text."""
    t = text.lower()
    if re.search(r'\b(twice|two times?|bd|b\.d)\b', t): return "BD"
    if re.search(r'\b(thrice|three times?|tid|t\.i\.d)\b', t): return "TID"
    if re.search(r'\b(four times?|qid|q\.i\.d)\b', t): return "QID"
    if re.search(r'\b(when needed|as needed|sos|s\.o\.s|prn)\b', t): return "SOS"
    if re.search(r'\b(at night|bedtime|hs|h\.s)\b', t): return "HS"
    if re.search(r'\b(once\s+daily|once\s+a\s+day|od|o\.d)\b', t): return "OD"
    if re.search(r'\b(daily)\b', t): return "OD"
    return ""


def _parse_instruction(text: str) -> str:
    """Extract food/timing instruction from text."""
    t = text.lower()
    if re.search(r'\b(after food|after meal|after eating|post[-\s]?meal)\b', t): return "After food"
    if re.search(r'\b(before food|before meal|before eating|pre[-\s]?meal)\b', t): return "Before food"
    if re.search(r'\b(with food|with meal|during meal)\b', t): return "With food"
    if re.search(r'\b(empty stomach|on empty stomach)\b', t): return "On empty stomach"
    return ""


def parse_medicines_from_text(text: str, db_medicines: list = None) -> list:
    """
    Parse a natural-language prescription text into a structured list of medicines.

    First runs the RapidFuzz correction engine on the full text, then extracts
    structured prescription data.

    Args:
        text: Raw transcription text
        db_medicines: Optional list of medicine names from database

    Returns:
        List of dicts: [{"name", "dosage", "frequency", "duration", "instructions", "corrected", "confidence"}, ...]
    """
    if not text or not text.strip():
        return []

    # ── Step 1: Run medicine correction engine on the full text ──
    correction_result = correct_full_text(text, db_medicines)
    corrected_text = correction_result["corrected_text"]
    corrections_map = {c["original"].lower(): c for c in correction_result["corrections"]}

    logger.info(f"[VOICE] Parsing text: original=\"{text[:80]}...\" corrected=\"{corrected_text[:80]}...\"")

    # ── Step 2: Parse the corrected text ──
    has_keywords = bool(re.search(r'\b(medicine|dose|dosage|frequency|duration|instruction)\b', corrected_text, re.I))

    if has_keywords:
        medicines = _parse_command_mode(corrected_text, db_medicines)
    else:
        medicines = _parse_freeform_mode(corrected_text, db_medicines)

    # ── Step 3: Mark medicines that were corrected ──
    for med in medicines:
        med_lower = med["name"].lower()
        for orig, corr in corrections_map.items():
            if corr["corrected"].lower() == med_lower:
                med["corrected"] = True
                med["confidence"] = corr["confidence"]
                med["suggestions"] = corr.get("suggestions", [])
                break

    return medicines


def _parse_command_mode(text: str, db_medicines: list = None) -> list:
    """Parse command-style text: 'medicine X dose Y frequency Z ...'"""
    blocks = re.split(r'\b(?:next medicine|next med|next)\b', text, flags=re.I)
    blocks = [b.strip() for b in blocks if b.strip() and len(b.strip()) > 2]

    results = []
    seen = set()

    for block in blocks:
        parsed = _parse_command_block(block, db_medicines)
        if parsed and parsed["name"].lower() not in seen:
            seen.add(parsed["name"].lower())
            results.append(parsed)

    return results


def _parse_command_block(block: str, db_medicines: list = None) -> dict:
    """Parse a single command block into medicine fields."""
    txt = block.strip()

    med_name = ""
    dose_str = ""
    freq_str = ""
    dur_str = ""
    inst_str = ""

    # Extract MEDICINE NAME
    med_match = re.search(
        r'\b(?:medicine(?:\s+name)?|med)\s*[:\s]\s*(.+?)(?=\s+(?:dose|dosage|frequency|freq|duration|dur|instruction|inst|for\s+\d)|$)',
        txt, re.I
    )
    if med_match:
        med_name = med_match.group(1).strip()
        inline_dose = re.match(r'^(.+?)\s+(\d+\s*(?:mg|ml|g|mcg|tablets?|capsules?|drops?|units?|iu))\s*$', med_name, re.I)
        if inline_dose:
            med_name = inline_dose.group(1).strip()
            dose_str = inline_dose.group(2).strip()

    # Extract DOSAGE
    dose_match = re.search(r'\b(?:dose|dosage)\s*[:\s]\s*(\d+\s*(?:mg|ml|g|mcg|tablets?|capsules?|drops?|units?|iu)?)', txt, re.I)
    if dose_match:
        dose_str = dose_match.group(1).strip()

    if not dose_str:
        standalone = re.search(r'(\d+\s*(?:mg|ml|g|mcg|tablets?|capsules?|drops?|units?|iu))', txt, re.I)
        if standalone:
            dose_str = standalone.group(1).strip()

    # Extract FREQUENCY
    freq_match = re.search(r'\b(?:frequency|freq)\s*[:\s]\s*(.+?)(?=\s+(?:duration|dur|instruction|inst|for\s+\d)|$)', txt, re.I)
    if freq_match:
        freq_str = _parse_frequency(freq_match.group(1).strip())
    if not freq_str:
        freq_str = _parse_frequency(txt)

    # Extract DURATION
    dur_match = re.search(r'\b(?:duration|dur)\s*[:\s]\s*(.+?)(?=\s+(?:instruction|inst)|$)', txt, re.I)
    if dur_match:
        dur_str = dur_match.group(1).strip()
    if not dur_str:
        for_match = re.search(r'\bfor\s+(\d+\s*(?:days?|weeks?|months?))', txt, re.I)
        if for_match:
            dur_str = for_match.group(1).strip()

    # Extract INSTRUCTION
    inst_match = re.search(r'\b(?:instruction|inst)\s*[:\s]\s*(.+?)$', txt, re.I)
    if inst_match:
        inst_str = inst_match.group(1).strip()
    if not inst_str:
        inst_str = _parse_instruction(txt)

    # If no name found via keyword → extract from beginning
    if not med_name:
        cleaned = re.sub(r'\b(?:dose|dosage|frequency|freq|duration|dur|instruction|inst)\s*[:\s].*', '', txt, flags=re.I)
        cleaned = re.sub(r'\d+\s*(?:mg|ml|g|mcg|tablets?|capsules?|drops?|units?|iu)', '', cleaned, flags=re.I)
        cleaned = re.sub(r'\b(twice|thrice|once|daily|bd|tid|qid|sos|hs|od)\b', '', cleaned, flags=re.I)
        cleaned = re.sub(r'\b(after|before|with)\s+(food|meal)\b', '', cleaned, flags=re.I)
        cleaned = re.sub(r'\bfor\s+\d+\s*(days?|weeks?|months?)', '', cleaned, flags=re.I)
        cleaned = re.sub(r'\b(take|prescribe|give)\b', '', cleaned, flags=re.I)
        med_name = cleaned.strip()

    if not med_name or len(med_name) < 2:
        return None

    # Fuzzy-match medicine name
    match_result = correct_medicine_name(med_name, db_medicines)

    return {
        "name": match_result["name"],
        "dosage": dose_str,
        "frequency": freq_str,
        "duration": dur_str,
        "instructions": inst_str,
        "corrected": match_result["corrected"],
        "confidence": match_result["confidence"],
        "suggestions": match_result.get("suggestions", []),
    }


def _parse_freeform_mode(text: str, db_medicines: list = None) -> list:
    """Parse free-form text: 'Paracetamol 500 mg twice daily, Amoxicillin 250 mg after food'"""
    segments = re.split(r'\s*(?:,|;|\band\b|\bthen\b)\s*', text, flags=re.I)
    segments = [s.strip() for s in segments if s.strip() and len(s.strip()) > 2]

    results = []
    seen = set()

    for seg in segments:
        parsed = _parse_freeform_segment(seg, db_medicines)
        if parsed and parsed["name"].lower() not in seen:
            seen.add(parsed["name"].lower())
            results.append(parsed)

    return results


def _parse_freeform_segment(text: str, db_medicines: list = None) -> dict:
    """Parse a single free-form segment into medicine fields."""
    txt = text.strip()
    if len(txt) < 3:
        return None

    # Extract dosage
    dose_match = re.search(r'(\d+\s*(?:mg|ml|g|mcg|tablets?|capsules?|drops?|units?|iu))', txt, re.I)
    dose_str = dose_match.group(0).strip() if dose_match else ""

    # Extract frequency
    freq_str = _parse_frequency(txt)

    # Extract duration
    dur_match = re.search(r'(?:for\s+)?(\d+\s*(?:days?|weeks?|months?))', txt, re.I)
    dur_str = dur_match.group(1).strip() if dur_match else ""

    # Extract instruction
    inst_str = _parse_instruction(txt)

    # Extract medicine name (everything else)
    med_name = txt
    med_name = re.sub(r'\d+\s*(?:mg|ml|g|mcg|tablets?|capsules?|drops?|units?|iu)', '', med_name, flags=re.I)
    med_name = re.sub(r'\b(twice|thrice|once|two times?|three times?|four times?)\b', '', med_name, flags=re.I)
    med_name = re.sub(r'\b(daily|bd|tid|qid|sos|hs|od|prn)\b', '', med_name, flags=re.I)
    med_name = re.sub(r'\b(after|before|with)\s+(food|meal|eating)\b', '', med_name, flags=re.I)
    med_name = re.sub(r'\b(on empty stomach|post[-\s]?meal|pre[-\s]?meal|during meal)\b', '', med_name, flags=re.I)
    med_name = re.sub(r'\bfor\b', '', med_name, flags=re.I)
    med_name = re.sub(r'\d+\s*(?:days?|weeks?|months?)', '', med_name, flags=re.I)
    med_name = re.sub(r'\b(take|prescribe|give|administer|at night|bedtime|when needed|as needed)\b', '', med_name, flags=re.I)
    med_name = re.sub(r'[,;]', '', med_name)
    med_name = re.sub(r'\s+', ' ', med_name).strip()

    if len(med_name) < 2:
        return None

    # Fuzzy-match
    match_result = correct_medicine_name(med_name, db_medicines)

    return {
        "name": match_result["name"],
        "dosage": dose_str,
        "frequency": freq_str,
        "duration": dur_str,
        "instructions": inst_str,
        "corrected": match_result["corrected"],
        "confidence": match_result["confidence"],
        "suggestions": match_result.get("suggestions", []),
    }
