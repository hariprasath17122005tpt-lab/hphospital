"""
Voice API Routes — AI Voice-to-Prescription System
====================================================
Endpoints:
  POST /voice/transcribe        — Upload audio, get Whisper transcription
  POST /voice/parse-medicines   — Parse text into structured medicines
  POST /voice/full-pipeline     — Audio → Transcription → Parsed medicines (one call)
  POST /voice/correct-text      — Correct medicine names in text (RapidFuzz)
  POST /voice/suggest-medicines — Get medicine suggestions for a word
  POST /check_medicine          — Check medicine availability in pharmacy
"""

import os
import logging
import time
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from app.routes.auth import doctor_required

logger = logging.getLogger(__name__)

voice_bp = Blueprint('voice', __name__, url_prefix='/voice')

_DB_MED_CACHE = {"values": [], "ts": 0.0}
_DB_MED_CACHE_TTL = int(os.getenv("VOICE_DB_MED_CACHE_TTL", "300"))


# ══════════════════════════════════════════════════════════════════════════════
#  POST /voice/transcribe — Whisper speech-to-text
# ══════════════════════════════════════════════════════════════════════════════

@voice_bp.route('/transcribe', methods=['POST'])
@login_required
@doctor_required
def voice_to_text():
    """
    Accept audio file upload, transcribe using Faster-Whisper.

    Input:  multipart/form-data with 'audio' file
    Output: { "success": true, "text": "Paracetamol 500 mg twice daily..." }
    """
    from app.services.voice_service import save_uploaded_audio, transcribe_audio

    if 'audio' not in request.files:
        return jsonify({'success': False, 'error': 'No audio file provided. Send as "audio" field.'}), 400

    audio_file = request.files['audio']
    if not audio_file or audio_file.filename == '':
        return jsonify({'success': False, 'error': 'Empty audio file received.'}), 400

    temp_path = None
    try:
        temp_path = save_uploaded_audio(audio_file)

        file_size = os.path.getsize(temp_path)
        if file_size < 1000:
            return jsonify({'success': False, 'error': 'Audio file too small. Please speak clearly.'}), 400
        if file_size > 50 * 1024 * 1024:
            return jsonify({'success': False, 'error': 'Audio file too large. Maximum 50MB.'}), 400

        result = transcribe_audio(temp_path)

        if result['success']:
            logger.info(f"[VOICE] Transcribed for user {current_user.id}: \"{result['text'][:60]}...\"")
            return jsonify(result)
        else:
            return jsonify(result), 500

    except RuntimeError as e:
        logger.error(f"[VOICE] Whisper error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    except Exception as e:
        logger.error(f"[VOICE] Unexpected error: {e}")
        return jsonify({
            'success': False,
            'error': f'Transcription failed: {str(e)}'
        }), 500
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception:
                pass


# ══════════════════════════════════════════════════════════════════════════════
#  POST /voice/parse-medicines — Parse text into structured medicines
# ══════════════════════════════════════════════════════════════════════════════

@voice_bp.route('/parse-medicines', methods=['POST'])
@login_required
@doctor_required
def parse_medicines():
    """
    Parse natural-language text into structured prescription data.
    Applies RapidFuzz medicine correction before parsing.

    Input:  { "text": "parasitamol 500 mg twice daily, amoxicilin 250 mg after food" }
    Output: {
        "success": true,
        "medicines": [
            { "name": "Paracetamol", "dosage": "500 mg", "frequency": "BD", "corrected": true, ... },
            ...
        ]
    }
    """
    from app.services.voice_service import parse_medicines_from_text

    data = request.get_json(silent=True) or {}
    text = data.get('text', '').strip()

    if not text:
        return jsonify({'success': False, 'error': 'No text provided for parsing.'}), 400

    db_medicines = _get_db_medicine_names()
    medicines = parse_medicines_from_text(text, db_medicines)

    return jsonify({
        'success': True,
        'medicines': medicines,
        'raw_text': text,
    })


# ══════════════════════════════════════════════════════════════════════════════
#  POST /voice/correct-text — Correct medicine names in text (NEW)
# ══════════════════════════════════════════════════════════════════════════════

@voice_bp.route('/correct-text', methods=['POST'])
@login_required
@doctor_required
def correct_text():
    """
    Correct medicine names in a raw transcription using RapidFuzz.

    Input:  { "text": "parasitamol 500 mg twice daily" }
    Output: {
        "success": true,
        "corrected_text": "Paracetamol 500 mg twice daily",
        "corrections": [
            { "original": "parasitamol", "corrected": "Paracetamol", "confidence": "high", "suggestions": [...] }
        ],
        "original": "parasitamol 500 mg twice daily"
    }
    """
    from app.services.voice_service import correct_full_text

    data = request.get_json(silent=True) or {}
    text = data.get('text', '').strip()

    if not text:
        return jsonify({'success': False, 'error': 'No text provided.'}), 400

    db_medicines = _get_db_medicine_names()
    result = correct_full_text(text, db_medicines)

    return jsonify({
        'success': True,
        **result,
    })


# ══════════════════════════════════════════════════════════════════════════════
#  POST /voice/suggest-medicines — Get medicine suggestions (NEW)
# ══════════════════════════════════════════════════════════════════════════════

@voice_bp.route('/suggest-medicines', methods=['POST'])
@login_required
@doctor_required
def suggest_medicines():
    """
    Get multiple medicine suggestions for a potentially misspelled word.
    Used to power the "Did you mean?" popup.

    Input:  { "word": "parasitamol" }
    Output: {
        "success": true,
        "word": "parasitamol",
        "suggestions": [
            { "name": "Paracetamol", "score": 92.5 },
            { "name": "Paracip", "score": 68.3 },
            ...
        ]
    }
    """
    from app.services.voice_service import get_medicine_suggestions

    data = request.get_json(silent=True) or {}
    word = data.get('word', '').strip()
    limit = min(data.get('limit', 5), 10)

    if not word:
        return jsonify({'success': False, 'error': 'No word provided.'}), 400

    db_medicines = _get_db_medicine_names()
    suggestions = get_medicine_suggestions(word, db_medicines, limit=limit)

    return jsonify({
        'success': True,
        'word': word,
        'suggestions': suggestions,
    })


# ══════════════════════════════════════════════════════════════════════════════
#  POST /voice/full-pipeline — Audio → Text → Corrected → Medicines (one call)
# ══════════════════════════════════════════════════════════════════════════════

@voice_bp.route('/full-pipeline', methods=['POST'])
@login_required
@doctor_required
def full_pipeline():
    """
    Complete voice-to-prescription pipeline:
    1. Upload audio → Whisper transcription
    2. RapidFuzz medicine correction
    3. Parse text → Structured medicines
    4. Return everything

    Input:  multipart/form-data with 'audio' file
    Output: {
        "success": true,
        "text": "...",
        "corrected_text": "...",
        "corrections": [...],
        "medicines": [...],
        "duration": 3.5
    }
    """
    from app.services.voice_service import (
        save_uploaded_audio, transcribe_audio,
        parse_medicines_from_text, correct_full_text
    )

    if 'audio' not in request.files:
        return jsonify({'success': False, 'error': 'No audio file. Send as "audio" field.'}), 400

    audio_file = request.files['audio']
    if not audio_file or audio_file.filename == '':
        return jsonify({'success': False, 'error': 'Empty audio file.'}), 400

    temp_path = None
    try:
        # Step 1: Save audio
        temp_path = save_uploaded_audio(audio_file)

        file_size = os.path.getsize(temp_path)
        if file_size < 1000:
            return jsonify({'success': False, 'error': 'Audio too short. Please speak louder/longer.'}), 400

        # Step 2: Transcribe
        transcription = transcribe_audio(temp_path)
        if not transcription['success']:
            return jsonify(transcription), 500

        raw_text = transcription['text']

        # Step 3: Correct medicine names with RapidFuzz
        db_medicines = _get_db_medicine_names()
        correction_result = correct_full_text(raw_text, db_medicines)

        # Step 4: Parse medicines from corrected text
        medicines = parse_medicines_from_text(raw_text, db_medicines)

        return jsonify({
            'success': True,
            'text': raw_text,
            'corrected_text': correction_result['corrected_text'],
            'corrections': correction_result['corrections'],
            'medicines': medicines,
            'segments': transcription.get('segments', []),
            'duration': transcription.get('duration', 0),
            'language': transcription.get('language', 'en'),
        })

    except RuntimeError as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        logger.error(f"[VOICE] Pipeline error: {e}")
        return jsonify({'success': False, 'error': f'Pipeline failed: {str(e)}'}), 500
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception:
                pass


# ══════════════════════════════════════════════════════════════════════════════
#  POST /check_medicine — Check pharmacy availability (NEW top-level endpoint)
# ══════════════════════════════════════════════════════════════════════════════

@voice_bp.route('/check-medicine', methods=['POST'])
@login_required
def check_medicine_availability():
    """
    Check a single medicine's availability in pharmacy inventory.

    Input:  { "medicine": "Paracetamol" }
    Output: { "name": "Paracetamol", "status": "available", "stock": 120 }
    """
    from app.models.models import db as app_db, Medicine

    data = request.get_json(silent=True) or {}
    medicine_name = data.get('medicine', '').strip()

    if not medicine_name:
        return jsonify({'success': False, 'error': 'Medicine name required.'}), 400

    # Case-insensitive lookup
    med = Medicine.query.filter(
        app_db.func.lower(Medicine.name) == medicine_name.lower()
    ).first()

    if med and med.stock > 0:
        return jsonify({
            'name': med.name,
            'status': 'available',
            'stock': med.stock,
        })
    elif med and med.stock == 0:
        return jsonify({
            'name': med.name,
            'status': 'out_of_stock',
            'stock': 0,
        })
    else:
        return jsonify({
            'name': medicine_name,
            'status': 'not_available',
            'stock': 0,
        })


# ══════════════════════════════════════════════════════════════════════════════
#  BROWSER-BASED SPEECH CORRECTION (text-only, no Whisper needed)
# ══════════════════════════════════════════════════════════════════════════════

@voice_bp.route('/browser-speech-correct', methods=['POST'])
@login_required
@doctor_required
def browser_speech_correct():
    """
    Accept text from the browser's Web Speech API and return corrected
    text with structured medicines. No Whisper model needed.

    Input:  { "text": "parasitamol 500 mg twice daily" }
    Output: {
        "success": true,
        "text": "parasitamol 500 mg twice daily",
        "corrected_text": "Paracetamol 500 mg twice daily",
        "corrections": [...],
        "medicines": [...]
    }
    """
    from app.services.voice_service import correct_full_text, parse_medicines_from_text

    data = request.get_json(silent=True) or {}
    text = data.get('text', '').strip()

    if not text:
        return jsonify({'success': False, 'error': 'No text provided.'}), 400

    db_medicines = _get_db_medicine_names()

    # Correct medicine names
    correction_result = correct_full_text(text, db_medicines)

    # Parse into structured medicines
    medicines = parse_medicines_from_text(text, db_medicines)

    return jsonify({
        'success': True,
        'text': text,
        'corrected_text': correction_result['corrected_text'],
        'corrections': correction_result['corrections'],
        'medicines': medicines,
    })


# ══════════════════════════════════════════════════════════════════════════════
#  HELPER
# ══════════════════════════════════════════════════════════════════════════════

def _get_db_medicine_names() -> list:
    """Fetch medicine names from the database for better fuzzy matching."""
    now = time.time()
    if _DB_MED_CACHE["values"] and (now - _DB_MED_CACHE["ts"] < _DB_MED_CACHE_TTL):
        return _DB_MED_CACHE["values"]

    try:
        from app.models.models import Medicine
        medicines = Medicine.query.all()
        names = [m.name for m in medicines if m.name]
        _DB_MED_CACHE["values"] = names
        _DB_MED_CACHE["ts"] = now
        return names
    except Exception as e:
        logger.warning(f"[VOICE] Could not fetch DB medicines: {e}")
        return []
