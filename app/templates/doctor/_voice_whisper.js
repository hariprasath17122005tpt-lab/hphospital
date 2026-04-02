// ══════════════════════════════════════════════════════════════
//  VOICE PRESCRIPTION SYSTEM — RapidFuzz Medicine Correction
//  Dual-mode: Browser Speech API + Whisper Backend
//  Features:
//    • Browser Web Speech API (primary, no server needed)
//    • Whisper backend (fallback for complex audio)
//    • RapidFuzz medicine name correction
//    • "Did you mean?" suggestion popup
//    • Pharmacy inventory verification
// ══════════════════════════════════════════════════════════════

let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let recordingStream = null;
let recordingTimer = null;
let recordingSeconds = 0;
let speechRecognition = null;
let useBrowserSpeech = true; // Prefer browser Speech API

const voiceFeedback = document.getElementById('voiceFeedback');
const transcriptPanel = document.getElementById('voiceTranscriptPanel');
const transcriptText = document.getElementById('transcriptText');
const parsedPillsEl = document.getElementById('parsedPills');
const btnVoice = document.getElementById('btnVoice');


// ══════════════════════════════════════════════════════════════
//  BROWSER SPEECH RECOGNITION SETUP
// ══════════════════════════════════════════════════════════════

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

if (SpeechRecognition) {
    speechRecognition = new SpeechRecognition();
    speechRecognition.continuous = true;
    speechRecognition.interimResults = true;
    speechRecognition.lang = 'en-IN';
    speechRecognition.maxAlternatives = 3;

    let finalTranscript = '';
    let interimTranscript = '';

    speechRecognition.onresult = function (event) {
        interimTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
                finalTranscript += transcript + ' ';
            } else {
                interimTranscript = transcript;
            }
        }

        // Update live transcript display
        const displayText = finalTranscript + (interimTranscript ? `<span style="color:#94a3b8;font-style:italic;">${interimTranscript}</span>` : '');
        transcriptText.innerHTML = `<span style="color:#ef4444;">● Live</span> ${displayText}`;
    };

    speechRecognition.onerror = function (event) {
        console.warn('Speech recognition error:', event.error);
        if (event.error === 'not-allowed') {
            voiceFeedback.textContent = '❌ Microphone access denied. Please allow mic access.';
            voiceFeedback.className = 'voice-feedback error';
            useBrowserSpeech = false;
        }
    };

    speechRecognition.onend = function () {
        if (isRecording && useBrowserSpeech) {
            // Auto-restart if still recording (continuous mode can stop)
            try { speechRecognition.start(); } catch (e) { }
        }
    };
} else {
    useBrowserSpeech = false;
    console.info('[VOICE] Browser Speech API not available, using Whisper backend only.');
}


// ─── TOGGLE RECORDING ───
function toggleVoiceRecording() {
    if (isRecording) {
        stopRecording();
    } else {
        startRecording();
    }
}


// ─── START RECORDING ───
async function startRecording() {
    try {
        isRecording = true;
        recordingSeconds = 0;

        // UI updates
        btnVoice.classList.add('recording');
        btnVoice.innerHTML = '<i class="fas fa-stop-circle"></i> Stop Recording <span id="recTimer" style="margin-left:8px;font-size:0.85rem;opacity:0.8;">0s</span>';
        voiceFeedback.textContent = '🔴 Recording... Speak your prescription clearly';
        voiceFeedback.className = 'voice-feedback';
        transcriptPanel.classList.add('active');
        transcriptText.innerHTML = '<span style="color:#ef4444;">● Recording...</span> Speak prescription now';
        parsedPillsEl.innerHTML = '';

        // Timer
        recordingTimer = setInterval(() => {
            recordingSeconds++;
            const timerEl = document.getElementById('recTimer');
            if (timerEl) timerEl.textContent = recordingSeconds + 's';

            if (recordingSeconds >= 120) {
                stopRecording();
            }
        }, 1000);

        if (useBrowserSpeech && speechRecognition) {
            // ── Browser Speech API Mode ──
            speechRecognition._finalTranscript = '';
            speechRecognition.onresult = function (event) {
                let interimTranscript = '';
                let finalTranscript = speechRecognition._finalTranscript || '';

                for (let i = event.resultIndex; i < event.results.length; i++) {
                    const transcript = event.results[i][0].transcript;
                    if (event.results[i].isFinal) {
                        finalTranscript += transcript + ' ';
                        speechRecognition._finalTranscript = finalTranscript;
                    } else {
                        interimTranscript = transcript;
                    }
                }

                const displayText = finalTranscript +
                    (interimTranscript ? `<span style="color:#94a3b8;font-style:italic;">${interimTranscript}</span>` : '');
                transcriptText.innerHTML = `<span style="color:#ef4444;">● Live</span> ${displayText}`;
            };

            try {
                speechRecognition.start();
                voiceFeedback.textContent = '🔴 Recording with Browser Speech Recognition...';
            } catch (e) {
                console.warn('Browser speech start failed, falling back to Whisper:', e);
                useBrowserSpeech = false;
                await startWhisperRecording();
            }
        } else {
            // ── Whisper Backend Mode ──
            await startWhisperRecording();
        }

    } catch (err) {
        console.error('Recording start failed:', err);
        isRecording = false;
        clearInterval(recordingTimer);
        voiceFeedback.textContent = '❌ Could not start recording: ' + err.message;
        voiceFeedback.className = 'voice-feedback error';
        btnVoice.classList.remove('recording');
        btnVoice.innerHTML = '<i class="fas fa-microphone"></i> Start Voice Dictation';
    }
}


// ─── START WHISPER RECORDING (MediaRecorder) ───
async function startWhisperRecording() {
    recordingStream = await navigator.mediaDevices.getUserMedia({
        audio: {
            channelCount: 1,
            sampleRate: 16000,
            echoCancellation: true,
            noiseSuppression: true,
        }
    });

    let mimeType = 'audio/webm;codecs=opus';
    if (!MediaRecorder.isTypeSupported(mimeType)) mimeType = 'audio/webm';
    if (!MediaRecorder.isTypeSupported(mimeType)) mimeType = 'audio/ogg;codecs=opus';
    if (!MediaRecorder.isTypeSupported(mimeType)) mimeType = '';

    const options = mimeType ? { mimeType } : {};
    mediaRecorder = new MediaRecorder(recordingStream, options);
    audioChunks = [];

    mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunks.push(event.data);
    };

    mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunks, { type: mimeType || 'audio/webm' });
        sendAudioToWhisper(audioBlob);
        if (recordingStream) {
            recordingStream.getTracks().forEach(t => t.stop());
            recordingStream = null;
        }
    };

    mediaRecorder.start(250);
    voiceFeedback.textContent = '🔴 Recording with AI Whisper backend...';
}


// ─── STOP RECORDING ───
function stopRecording() {
    clearInterval(recordingTimer);
    isRecording = false;

    btnVoice.classList.remove('recording');
    btnVoice.innerHTML = '<i class="fas fa-microphone"></i> Start Voice Dictation';

    if (useBrowserSpeech && speechRecognition) {
        // ── Browser Speech API Mode: stop and process ──
        try { speechRecognition.stop(); } catch (e) { }

        const rawText = (speechRecognition._finalTranscript || '').trim();
        speechRecognition._finalTranscript = '';

        if (!rawText || rawText.length < 3) {
            voiceFeedback.textContent = '⚠ No speech detected. Please try again.';
            voiceFeedback.className = 'voice-feedback error';
            transcriptText.textContent = 'No speech was recognized. Try speaking louder.';
            return;
        }

        // Send to RapidFuzz correction engine
        voiceFeedback.textContent = '⏳ Correcting medicine names with AI...';
        voiceFeedback.className = 'voice-feedback';
        transcriptText.innerHTML = `<strong>Raw Speech:</strong> "${rawText}"<br><i class="fas fa-spinner fa-spin" style="color:#6366f1;"></i> Running medicine correction...`;

        sendToCorrectionEngine(rawText);

    } else if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        // ── Whisper Mode: stop MediaRecorder ──
        mediaRecorder.stop();
        voiceFeedback.textContent = '⏳ Processing audio with AI Whisper...';
        voiceFeedback.className = 'voice-feedback';
        transcriptText.innerHTML = '<i class="fas fa-spinner fa-spin" style="color:#6366f1;"></i> Sending to AI Whisper for transcription...';
    }
}


// ══════════════════════════════════════════════════════════════
//  RAPIDFUZZ CORRECTION ENGINE (Browser Speech → Server)
// ══════════════════════════════════════════════════════════════

async function sendToCorrectionEngine(rawText) {
    try {
        btnVoice.disabled = true;
        btnVoice.innerHTML = '<i class="fas fa-spinner fa-spin"></i> AI Correcting...';

        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;

        const response = await fetch('/voice/browser-speech-correct', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...(csrfToken ? { 'X-CSRFToken': csrfToken } : {}),
            },
            body: JSON.stringify({ text: rawText }),
        });

        const data = await response.json();

        if (data.success) {
            // Display correction info
            let correctionHtml = `<strong>Original:</strong> "${data.text}"<br>`;

            if (data.corrections && data.corrections.length > 0) {
                correctionHtml += `<strong style="color:#10b981;">Corrected:</strong> "${data.corrected_text}"<br>`;
                correctionHtml += `<div style="margin-top:6px;font-size:0.82rem;color:#a5b4fc;">`;
                data.corrections.forEach(c => {
                    correctionHtml += `<span style="background:rgba(99,102,241,0.1);padding:2px 8px;border-radius:8px;margin:2px;display:inline-block;">
                        <s style="color:#f87171;">${c.original}</s> → <strong style="color:#34d399;">${c.corrected}</strong>
                        <span style="opacity:0.6;font-size:0.75rem;">(${c.confidence})</span>
                    </span>`;
                });
                correctionHtml += '</div>';
                voiceFeedback.textContent = `✓ Corrected ${data.corrections.length} medicine name(s)`;
                voiceFeedback.className = 'voice-feedback success';
            } else {
                voiceFeedback.textContent = '✓ Speech recognized — no corrections needed';
                voiceFeedback.className = 'voice-feedback success';
            }

            transcriptText.innerHTML = correctionHtml;

            // Process medicines
            if (data.medicines && data.medicines.length > 0) {
                populateMedicinesFromCorrected(data.medicines);
            } else {
                // Fallback: try client-side parsing
                processVoiceCommand(data.corrected_text || data.text);
            }

            // Show suggestions for ambiguous matches
            showMedicineSuggestions(data.medicines || []);

        } else {
            voiceFeedback.textContent = '❌ ' + (data.error || 'Correction failed');
            voiceFeedback.className = 'voice-feedback error';
            // Fallback to client-side parsing
            processVoiceCommand(rawText);
        }

    } catch (err) {
        console.error('Correction engine error:', err);
        voiceFeedback.textContent = '⚠ Server unavailable — using local correction';
        voiceFeedback.className = 'voice-feedback';
        // Fallback to client-side matching
        processVoiceCommand(rawText);
    } finally {
        btnVoice.disabled = false;
        btnVoice.innerHTML = '<i class="fas fa-microphone"></i> Start Voice Dictation';
    }
}


// ── SEND AUDIO TO WHISPER BACKEND ──
async function sendAudioToWhisper(audioBlob) {
    if (audioBlob.size < 1000) {
        voiceFeedback.textContent = '⚠ Recording too short. Please speak for at least 2 seconds.';
        voiceFeedback.className = 'voice-feedback error';
        transcriptText.textContent = 'Recording was too short. Try again.';
        return;
    }

    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.webm');

    try {
        btnVoice.disabled = true;
        btnVoice.innerHTML = '<i class="fas fa-spinner fa-spin"></i> AI Processing...';

        const response = await fetch('/voice/full-pipeline', {
            method: 'POST',
            body: formData,
        });

        const data = await response.json();

        if (data.success && data.text) {
            // Show transcription with corrections
            let correctionHtml = `<strong>AI Transcript:</strong> "${data.text}"`;

            if (data.duration) {
                correctionHtml += ` <span style="color:#94a3b8;font-size:0.8rem;">(${data.duration}s audio)</span>`;
            }

            if (data.corrections && data.corrections.length > 0) {
                correctionHtml += `<br><strong style="color:#10b981;">Medicine Corrections:</strong><br>`;
                correctionHtml += `<div style="margin-top:4px;font-size:0.82rem;">`;
                data.corrections.forEach(c => {
                    correctionHtml += `<span style="background:rgba(99,102,241,0.1);padding:2px 8px;border-radius:8px;margin:2px;display:inline-block;">
                        <s style="color:#f87171;">${c.original}</s> → <strong style="color:#34d399;">${c.corrected}</strong>
                    </span>`;
                });
                correctionHtml += '</div>';
            }

            transcriptText.innerHTML = correctionHtml;
            voiceFeedback.textContent = '✓ Whisper transcription + medicine correction complete!';
            voiceFeedback.className = 'voice-feedback success';

            // Process medicines
            if (data.medicines && data.medicines.length > 0) {
                populateMedicinesFromCorrected(data.medicines);
            } else {
                processVoiceCommand(data.corrected_text || data.text);
            }

            showMedicineSuggestions(data.medicines || []);

        } else {
            const errorMsg = data.error || 'Transcription returned empty text';
            voiceFeedback.textContent = '❌ ' + errorMsg;
            voiceFeedback.className = 'voice-feedback error';
            transcriptText.textContent = 'Transcription failed: ' + errorMsg;
        }
    } catch (err) {
        console.error('Whisper API error:', err);
        voiceFeedback.textContent = '❌ Network error. Check if server is running.';
        voiceFeedback.className = 'voice-feedback error';
        transcriptText.textContent = 'Could not reach AI server. Please try again.';
    } finally {
        btnVoice.disabled = false;
        btnVoice.innerHTML = '<i class="fas fa-microphone"></i> Start Voice Dictation';
    }
}


// ══════════════════════════════════════════════════════════════
//  POPULATE TABLE FROM CORRECTED MEDICINES
// ══════════════════════════════════════════════════════════════

function populateMedicinesFromCorrected(medicines) {
    const existing = getExistingMedicines();
    let addedCount = 0;

    removeEmptyRows();

    medicines.forEach(med => {
        const name = med.name || '';
        if (!name || name.length < 2) return;

        if (existing.has(name.toLowerCase())) {
            addPill(name, 'duplicate', `⚠ ${name} (already added)`);
            return;
        }

        const freq = med.frequency || 'OD';

        medTableBody.appendChild(createRowElement(
            name,
            med.dosage || '',
            freq,
            med.duration || '',
            med.instructions || ''
        ));
        existing.add(name.toLowerCase());
        addedCount++;

        // Show correction pill
        if (med.corrected) {
            addPill(name, 'corrected', `✓ ${name} (auto-corrected)`);
        } else {
            addPill(name, 'added', `✓ ${name}`);
        }
    });

    if (addedCount > 0) {
        voiceFeedback.textContent = `✓ Added ${addedCount} medicine${addedCount > 1 ? 's' : ''} from voice recognition`;
        voiceFeedback.className = 'voice-feedback success';

        // Auto-verify with pharmacy
        autoVerifyMedicines(medicines.map(m => m.name));
    }
}


// ══════════════════════════════════════════════════════════════
//  MEDICINE SUGGESTION POPUP ("Did you mean?")
// ══════════════════════════════════════════════════════════════

function showMedicineSuggestions(medicines) {
    // Remove existing suggestion panel
    const existingPanel = document.getElementById('medicineSuggestionPanel');
    if (existingPanel) existingPanel.remove();

    // Filter medicines with suggestions and low/medium confidence
    const ambiguous = medicines.filter(m =>
        m.suggestions && m.suggestions.length > 1 &&
        m.confidence !== 'exact'
    );

    if (ambiguous.length === 0) return;

    const panel = document.createElement('div');
    panel.id = 'medicineSuggestionPanel';
    panel.style.cssText = `
        background: linear-gradient(135deg, rgba(245,158,11,0.08), rgba(234,88,12,0.04));
        border: 1px solid rgba(245,158,11,0.25);
        border-radius: 14px;
        padding: 16px 20px;
        margin-bottom: 18px;
        animation: fadeSlideDown 0.3s ease;
    `;

    let html = `
        <div style="font-weight:700;color:#f59e0b;font-size:0.85rem;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:12px;display:flex;align-items:center;gap:8px;">
            <i class="fas fa-question-circle"></i> Did you mean?
            <span style="font-size:0.75rem;opacity:0.7;text-transform:none;font-weight:400;">Click to select the correct medicine</span>
        </div>
    `;

    ambiguous.forEach((med, medIdx) => {
        html += `<div style="margin-bottom:12px;">`;
        html += `<div style="font-size:0.8rem;color:#94a3b8;margin-bottom:6px;">For: <strong style="color:#fbbf24;">"${med.name}"</strong></div>`;
        html += `<div style="display:flex;flex-wrap:wrap;gap:6px;">`;

        med.suggestions.forEach(s => {
            const isSelected = s.name === med.name;
            html += `
                <button onclick="selectSuggestion('${med.name}', '${s.name}', this)"
                    class="suggestion-btn ${isSelected ? 'selected' : ''}"
                    style="
                        background: ${isSelected ? 'rgba(16,185,129,0.15)' : 'rgba(30,41,59,0.6)'};
                        border: 1px solid ${isSelected ? 'rgba(16,185,129,0.3)' : 'rgba(148,163,184,0.15)'};
                        border-radius: 10px;
                        padding: 6px 14px;
                        cursor: pointer;
                        font-size: 0.85rem;
                        font-weight: 600;
                        color: ${isSelected ? '#34d399' : '#e2e8f0'};
                        transition: all 0.2s;
                    "
                    onmouseenter="this.style.transform='translateY(-1px)';this.style.boxShadow='0 3px 10px rgba(0,0,0,0.15)'"
                    onmouseleave="this.style.transform='none';this.style.boxShadow='none'"
                >
                    ${s.name}
                    <span style="font-size:0.7rem;opacity:0.6;margin-left:4px;">${s.score}%</span>
                </button>
            `;
        });

        html += `</div></div>`;
    });

    panel.innerHTML = html;

    // Insert before the prescription sheet
    const rxSheet = document.getElementById('prescriptionSheet');
    if (rxSheet) {
        rxSheet.parentNode.insertBefore(panel, rxSheet);
    }
}


function selectSuggestion(currentName, newName, btnEl) {
    // Update the medicine name in the prescription table
    const rows = document.querySelectorAll('#medTableBody tr');
    rows.forEach(row => {
        const nameInput = row.querySelector('.med-name');
        if (nameInput && nameInput.value.trim().toLowerCase() === currentName.toLowerCase()) {
            nameInput.value = newName;

            // Flash the row green
            row.style.background = 'rgba(16,185,129,0.1)';
            setTimeout(() => { row.style.background = ''; }, 1500);
        }
    });

    // Update button styles
    const parentDiv = btnEl.parentNode;
    parentDiv.querySelectorAll('.suggestion-btn').forEach(btn => {
        btn.style.background = 'rgba(30,41,59,0.6)';
        btn.style.borderColor = 'rgba(148,163,184,0.15)';
        btn.style.color = '#e2e8f0';
    });
    btnEl.style.background = 'rgba(16,185,129,0.15)';
    btnEl.style.borderColor = 'rgba(16,185,129,0.3)';
    btnEl.style.color = '#34d399';

    // Update the pill display
    addPill(newName, 'corrected', `✓ ${newName} (selected)`);

    voiceFeedback.textContent = `✓ Updated: ${currentName} → ${newName}`;
    voiceFeedback.className = 'voice-feedback success';
}


// ── AUTO-VERIFY WITH PHARMACY ──
async function autoVerifyMedicines(medicineNames) {
    if (!medicineNames || medicineNames.length === 0) return;
    try {
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
        const resp = await fetch('/pharmacy-ops/api/check-medicines', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
            body: JSON.stringify({ medicines: medicineNames })
        });
        const results = await resp.json();
        if (Array.isArray(results)) {
            showPharmacyVerification(results);
        }
    } catch (e) {
        console.warn('Pharmacy verification skipped:', e);
    }
}


// ── SHOW PHARMACY VERIFICATION INLINE ──
function showPharmacyVerification(results) {
    let existingPanel = document.getElementById('inlinePharmacyCheck');
    if (existingPanel) existingPanel.remove();

    const panel = document.createElement('div');
    panel.id = 'inlinePharmacyCheck';
    panel.style.cssText = 'background:linear-gradient(135deg,rgba(99,102,241,0.06),rgba(16,185,129,0.04));border:1px solid rgba(99,102,241,0.2);border-radius:14px;padding:16px 20px;margin-bottom:24px;animation:fadeSlideDown 0.3s ease;';

    let html = '<div style="font-weight:700;color:#6366f1;font-size:0.85rem;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:12px;display:flex;align-items:center;gap:8px;"><i class="fas fa-clipboard-check"></i> Pharmacy Inventory Check</div>';

    // Summary badges
    const availCount = results.filter(m => m.status === 'available').length;
    const notAvailCount = results.length - availCount;
    html += '<div style="display:flex;gap:10px;margin-bottom:12px;flex-wrap:wrap;">';
    html += `<span style="background:rgba(16,185,129,0.12);color:#34d399;padding:4px 12px;border-radius:16px;font-size:0.78rem;font-weight:700;border:1px solid rgba(16,185,129,0.2);">✔ ${availCount} Available</span>`;
    if (notAvailCount > 0) {
        html += `<span style="background:rgba(239,68,68,0.12);color:#f87171;padding:4px 12px;border-radius:16px;font-size:0.78rem;font-weight:700;border:1px solid rgba(239,68,68,0.2);">❌ ${notAvailCount} Not Available</span>`;
    }
    html += '</div>';

    html += '<div style="display:flex;flex-wrap:wrap;gap:8px;">';

    results.forEach(med => {
        const isAvail = med.status === 'available';
        const bg = isAvail ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.08)';
        const border = isAvail ? 'rgba(16,185,129,0.25)' : 'rgba(239,68,68,0.2)';
        const color = isAvail ? '#059669' : '#dc2626';
        const icon = isAvail ? '✔' : '❌';
        const label = isAvail ? `${med.stock} in stock` : 'Not available';

        html += `<div style="background:${bg};border:1px solid ${border};border-radius:10px;padding:8px 14px;display:flex;align-items:center;gap:8px;">
                <span style="font-size:1.1rem;">${icon}</span>
                <div>
                    <div style="font-weight:600;color:#1e293b;font-size:0.9rem;">${med.name}</div>
                    <div style="font-size:0.75rem;color:${color};font-weight:600;">${label}</div>
                </div>
            </div>`;
    });

    html += '</div>';
    panel.innerHTML = html;

    const rxSheet = document.getElementById('prescriptionSheet');
    rxSheet.parentNode.insertBefore(panel, rxSheet);
}


// ══════════════════════════════════════════════════════════════
//  CLIENT-SIDE FALLBACK PARSER (used if server is unavailable)
// ══════════════════════════════════════════════════════════════

function processVoiceCommand(rawText) {
    const txt = rawText.trim();
    const txtLower = txt.toLowerCase();

    const hasKeywords = /\b(medicine|dose|dosage|frequency|duration|instruction)\b/i.test(txtLower);

    if (hasKeywords) {
        parseCommandMode(txt);
    } else {
        parseFreeformMode(txt);
    }
}

function parseCommandMode(rawText) {
    const existing = getExistingMedicines();
    const blocks = rawText.split(/\b(?:next medicine|next med|next)\b/i).map(b => b.trim()).filter(b => b.length > 2);
    let addedCount = 0;
    blocks.forEach(block => { if (parseCommandBlock(block, existing)) addedCount++; });
    removeEmptyRows();
    if (addedCount > 0) {
        voiceFeedback.textContent = `✓ Added ${addedCount} medicine${addedCount > 1 ? 's' : ''} to prescription`;
        voiceFeedback.className = 'voice-feedback success';
    } else {
        voiceFeedback.textContent = 'Could not parse. Try: "medicine Paracetamol dose 500mg twice daily"';
        voiceFeedback.className = 'voice-feedback error';
    }
}

function parseCommandBlock(block, existing) {
    const txt = block.trim();
    let medName = '', doseStr = '', freqStr = '', durStr = '', instStr = '';

    const medMatch = txt.match(/\b(?:medicine(?:\s+name)?|med)\s*[:\s]\s*(.+?)(?=\s+(?:dose|dosage|frequency|freq|duration|dur|instruction|inst|for\s+\d)|$)/i);
    if (medMatch) {
        medName = medMatch[1].trim();
        const inlineDose = medName.match(/^(.+?)\s+(\d+\s*(?:mg|ml|g|mcg|tablets?|capsules?|drops?|units?|iu))\s*$/i);
        if (inlineDose) { medName = inlineDose[1].trim(); if (!doseStr) doseStr = inlineDose[2].trim(); }
    }

    const doseMatch = txt.match(/\b(?:dose|dosage)\s*[:\s]\s*(\d+\s*(?:mg|ml|g|mcg|tablets?|capsules?|drops?|units?|iu)?)/i);
    if (doseMatch) doseStr = doseMatch[1].trim();
    if (!doseStr) { const sd = txt.match(/(\d+\s*(?:mg|ml|g|mcg|tablets?|capsules?|drops?|units?|iu))/i); if (sd) doseStr = sd[1].trim(); }

    freqStr = parseFrequency(txt);

    const durMatch = txt.match(/\b(?:duration|dur)\s*[:\s]\s*(.+?)(?=\s+(?:instruction|inst)|$)/i);
    if (durMatch) durStr = durMatch[1].trim();
    if (!durStr) { const fm = txt.match(/\bfor\s+(\d+\s*(?:days?|weeks?|months?))/i); if (fm) durStr = fm[1].trim(); }

    instStr = parseInstruction(txt);

    if (!medName) {
        let cleaned = txt.replace(/\b(?:dose|dosage|frequency|freq|duration|dur|instruction|inst)\s*[:\s].*/i, '')
            .replace(/\d+\s*(?:mg|ml|g|mcg|tablets?|capsules?|drops?|units?|iu)/gi, '')
            .replace(/\b(twice|thrice|once|daily|bd|tid|qid|sos|hs|od)\b/gi, '')
            .replace(/\b(after|before|with)\s+(food|meal)/gi, '')
            .replace(/\bfor\s+\d+\s*(days?|weeks?|months?)/gi, '')
            .replace(/\b(take|prescribe|give)\b/gi, '').trim();
        medName = cleaned;
    }

    if (!medName || medName.length < 2) return false;

    const matchResult = matchMedicineName(medName);
    medName = matchResult.name;

    if (existing.has(medName.toLowerCase())) { addPill(medName, 'duplicate', `⚠ ${medName} (already added)`); return false; }

    medTableBody.appendChild(createRowElement(medName, doseStr, freqStr, durStr, instStr));
    existing.add(medName.toLowerCase());
    if (matchResult.corrected) addPill(medName, 'corrected', `✓ ${medName} (auto-corrected)`);
    else addPill(medName, 'added', `✓ ${medName}`);
    return true;
}

function parseFreeformMode(rawText) {
    const existing = getExistingMedicines();
    const segments = rawText.split(/\s*(?:,|;|\band\b|\bthen\b)\s*/gi).map(s => s.trim()).filter(s => s.length > 2);
    let addedCount = 0;
    segments.forEach(seg => { if (parseFreeformSegment(seg, existing)) addedCount++; });
    removeEmptyRows();
    if (addedCount > 0) {
        voiceFeedback.textContent = `✓ Added ${addedCount} medicine${addedCount > 1 ? 's' : ''}`;
        voiceFeedback.className = 'voice-feedback success';
    } else {
        const notesEl = document.getElementById('valNotes');
        notesEl.value += (notesEl.value ? '\n' : '') + rawText;
        voiceFeedback.textContent = 'Added to notes. For medicines, try: "medicine [name] dose [dosage]"';
        voiceFeedback.className = 'voice-feedback';
    }
}

function parseFreeformSegment(text, existing) {
    const txt = text.toLowerCase().trim();
    if (txt.length < 3) return false;
    const doseMatch = txt.match(/(\d+\s*(?:mg|ml|g|mcg|tablets?|capsules?|drops?|units?|iu))/i);
    const doseStr = doseMatch ? doseMatch[0].trim() : '';
    const freqStr = parseFrequency(txt);
    const durMatch = txt.match(/(?:for\s+)?(\d+\s*(?:days?|weeks?|months?))/i);
    const durStr = durMatch ? durMatch[1].trim() : '';
    const instStr = parseInstruction(txt);

    let medName = text.trim()
        .replace(/\d+\s*(?:mg|ml|g|mcg|tablets?|capsules?|drops?|units?|iu)/gi, '')
        .replace(/\b(twice|thrice|once|two times?|three times?|four times?)\b/gi, '')
        .replace(/\b(daily|bd|tid|qid|sos|hs|od|prn)\b/gi, '')
        .replace(/\b(after|before|with)\s+(food|meal|eating)\b/gi, '')
        .replace(/\b(on empty stomach|post[-\s]?meal|pre[-\s]?meal|during meal)\b/gi, '')
        .replace(/\bfor\b/gi, '').replace(/\d+\s*(?:days?|weeks?|months?)/gi, '')
        .replace(/\b(take|prescribe|give|administer|at night|bedtime|when needed|as needed)\b/gi, '')
        .replace(/[,;]/g, '').replace(/\s+/g, ' ').trim();

    if (medName.length < 2) return false;
    const matchResult = matchMedicineName(medName);
    medName = matchResult.name;
    if (existing.has(medName.toLowerCase())) { addPill(medName, 'duplicate', `⚠ ${medName} (duplicate)`); return false; }
    medTableBody.appendChild(createRowElement(medName, doseStr, freqStr, durStr, instStr));
    existing.add(medName.toLowerCase());
    if (matchResult.corrected) addPill(medName, 'corrected', `✓ ${medName} (auto-corrected)`);
    else addPill(medName, 'added', `✓ ${medName}`);
    return true;
}

function previewPrescription() { window.print(); }
