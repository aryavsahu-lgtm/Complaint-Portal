/**
 * Audio Recorder Module
 * Handles recording, visualization, and playback of audio complaints.
 */

class AudioRecorderModule {
    constructor(config) {
        this.config = config;
        this.recordBtn = document.getElementById(config.recordBtnId);
        this.stopBtn = document.getElementById(config.stopBtnId);
        this.playback = document.getElementById(config.playbackId);
        this.canvas = document.getElementById(config.waveformId);
        this.statusSpan = document.getElementById(config.statusId);
        this.container = document.getElementById(config.containerId);
        this.visualizer = document.getElementById(config.visualizerId);
        this.resetBtn = document.getElementById(config.resetId);

        this.canvasCtx = this.canvas.getContext('2d');
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.audioContext = null;
        this.analyser = null;
        this.dataArray = null;
        this.animationId = null;
        this.stream = null;

        this.init();
    }

    init() {
        this.recordBtn.addEventListener('click', () => this.startRecording());
        this.stopBtn.addEventListener('click', () => this.stopRecording());
        this.resetBtn.addEventListener('click', () => this.resetRecording());

        // Form submission hijacking to append the audio blob
        const form = this.recordBtn.closest('form');
        if (form) {
            form.addEventListener('submit', (e) => this.handleSubmit(e));
        }
    }

    async startRecording() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });

            // --- BROWSER COMPATIBILITY: Detect supported mime types ---
            const types = ['audio/webm', 'audio/mp4', 'audio/ogg', 'audio/wav'];
            this.supportedType = '';
            for (const type of types) {
                if (MediaRecorder.isTypeSupported(type)) {
                    this.supportedType = type;
                    break;
                }
            }
            console.log('[Audio] Using mime type:', this.supportedType);

            const options = this.supportedType ? { mimeType: this.supportedType } : {};
            this.mediaRecorder = new MediaRecorder(this.stream, options);
            this.audioChunks = [];

            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };

            this.mediaRecorder.onstop = () => {
                const blobType = this.supportedType || 'audio/webm';
                const audioBlob = new Blob(this.audioChunks, { type: blobType });

                if (audioBlob.size === 0) {
                    console.error('[Audio] Recording produced an empty blob.');
                    this.updateStatus('Recording failed: No data captured.', 'danger');
                    return;
                }

                const audioUrl = URL.createObjectURL(audioBlob);
                this.playback.src = audioUrl;
                this.playback.load(); // Force reload

                this.container.classList.remove('d-none');
                this.visualizer.classList.add('d-none');
                this.audioBlob = audioBlob;
            };

            this.playback.onerror = () => {
                console.error('[Audio] Playback error encountered.');
                this.updateStatus('Playback error: Browser incompatible with format.', 'danger');
            };

            this.mediaRecorder.start(100); // Collect data every 100ms
            this.setupVisualizer();

            this.recordBtn.classList.add('d-none');
            this.stopBtn.classList.remove('d-none');
            this.visualizer.classList.remove('d-none');
            this.updateStatus('Recording...', 'danger');
        } catch (err) {
            console.error('Error accessing microphone:', err);
            this.updateStatus('Microphone access denied', 'danger');
        }
    }

    stopRecording() {
        if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
            this.mediaRecorder.stop();
            this.stream.getTracks().forEach(track => track.stop());
            cancelAnimationFrame(this.animationId);

            this.stopBtn.classList.add('d-none');
            this.recordBtn.classList.remove('d-none');
            this.recordBtn.innerHTML = '<i class="bi bi-mic"></i> Record Again';
            this.updateStatus('Recording finished', 'success');
        }
    }

    resetRecording() {
        this.audioChunks = [];
        this.audioBlob = null;
        this.playback.src = '';
        this.container.classList.add('d-none');
        this.updateStatus('Recording cleared', 'info');
        this.recordBtn.innerHTML = '<i class="bi bi-mic"></i> Start Recording';
    }

    setupVisualizer() {
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        this.analyser = this.audioContext.createAnalyser();
        const source = this.audioContext.createMediaStreamSource(this.stream);
        source.connect(this.analyser);

        this.analyser.fftSize = 256;
        const bufferLength = this.analyser.frequencyBinCount;
        this.dataArray = new Uint8Array(bufferLength);

        this.draw();
    }

    draw() {
        this.animationId = requestAnimationFrame(() => this.draw());
        this.analyser.getByteFrequencyData(this.dataArray);

        // Match internal dimensions to display dimensions
        if (this.canvas.width !== this.canvas.clientWidth || this.canvas.height !== this.canvas.clientHeight) {
            this.canvas.width = this.canvas.clientWidth;
            this.canvas.height = this.canvas.clientHeight;
        }

        this.canvasCtx.fillStyle = '#ffffff';
        this.canvasCtx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        const barWidth = (this.canvas.width / this.dataArray.length) * 2.5;
        let barHeight;
        let x = 0;

        for (let i = 0; i < this.dataArray.length; i++) {
            barHeight = (this.dataArray[i] / 255) * this.canvas.height;

            // Nice gradient color
            this.canvasCtx.fillStyle = `rgb(50, 150, 255)`;
            this.canvasCtx.fillRect(x, this.canvas.height - barHeight, barWidth, barHeight);

            x += barWidth + 1;
        }
    }

    updateStatus(msg, type) {
        this.statusSpan.textContent = msg;
        this.statusSpan.className = `badge bg-${type} status-badge`;
        this.statusSpan.classList.remove('display-none');
    }

    handleSubmit(event) {
        if (this.audioBlob) {
            // Determine extension from mime type
            let ext = 'webm';
            if (this.supportedType && this.supportedType.includes('mp4')) ext = 'mp4';
            else if (this.supportedType && this.supportedType.includes('ogg')) ext = 'ogg';
            else if (this.supportedType && this.supportedType.includes('wav')) ext = 'wav';

            const dataTransfer = new DataTransfer();
            const file = new File([this.audioBlob], `complaint_voice.${ext}`, { type: this.supportedType || "audio/webm" });
            dataTransfer.items.add(file);

            const fileInput = document.getElementById('audio-data');
            if (fileInput) {
                fileInput.files = dataTransfer.files;
            }
        }
    }
}

/**
 * Voice Input Module for Tracking
 * Uses SpeechRecognition to capture voice commands for status tracking.
 */
class VoiceInputModule {
    constructor(config) {
        this.config = config;
        this.btn = document.getElementById(config.btnId);
        this.status = document.getElementById(config.statusId);
        this.recognition = null;
        this.isListening = false;

        this.init();
    }

    init() {
        if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
            console.error('Speech recognition not supported');
            if (this.btn) this.btn.style.display = 'none';
            return;
        }

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();
        this.recognition.continuous = false;
        this.recognition.interimResults = false;
        this.recognition.lang = 'en-IN'; // Support Indian English

        this.btn.addEventListener('click', () => this.toggleListening());

        this.recognition.onstart = () => {
            this.isListening = true;
            this.btn.classList.add('btn-danger', 'pulse-animation');
            this.btn.classList.remove('btn-primary');
            this.btn.innerHTML = '<i class="bi bi-stop-fill"></i> Listening...';
            this.updateStatus('Listening for status request...', 'info');
        };

        this.recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            console.log('Voice result:', transcript);
            this.handleTranscript(transcript);
        };

        this.recognition.onerror = (event) => {
            console.error('Recognition error:', event.error);
            this.stopListening();
            this.updateStatus('Error: ' + event.error, 'danger');
        };

        this.recognition.onend = () => {
            this.stopListening();
        };
    }

    toggleListening() {
        if (this.isListening) {
            this.recognition.stop();
        } else {
            this.recognition.start();
        }
    }

    stopListening() {
        this.isListening = false;
        this.btn.classList.remove('btn-danger', 'pulse-animation');
        this.btn.classList.add('btn-primary');
        this.btn.innerHTML = '<i class="bi bi-mic-fill"></i> Ask Status';
    }

    updateStatus(msg, type) {
        if (!this.status) return;
        this.status.textContent = msg;
        this.status.className = `badge bg-${type} me-2`;
    }

    async handleTranscript(text) {
        this.updateStatus('AI is checking: "' + text + '"', 'warning');

        try {
            const response = await fetch('/chatbot/voice-status', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ transcript: text })
            });

            const data = await response.json();

            if (data.success) {
                this.updateStatus('Found: #' + data.complaint_id, 'success');

                // 1. Speak the AI message
                this.speak(data.message);

                // 2. Highlight/Filter the row in the table
                const searchInput = document.querySelector('input[name="search"]');
                if (searchInput) {
                    searchInput.value = '#' + data.complaint_id;
                    setTimeout(() => {
                        searchInput.form.submit();
                    }, 4000); // Submit after someone starts speaking
                }
            } else {
                this.updateStatus('Not found', 'danger');
                this.speak(data.message || "I couldn't find a matching complaint.");
            }
        } catch (error) {
            console.error('Voice status error:', error);
            this.updateStatus('Error connecting to AI', 'danger');
            this.speak("Sorry, I'm having trouble connecting to the portal right now.");
        }
    }

    speak(text) {
        if (!('speechSynthesis' in window)) return;

        // Cancel any current speech
        window.speechSynthesis.cancel();

        const utterance = new SpeechSynthesisUtterance(text);

        // Use a natural sounding voice
        const voices = window.speechSynthesis.getVoices();
        const preferredVoice = voices.find(v => v.lang.includes('en-IN')) || voices.find(v => v.lang.includes('en'));
        if (preferredVoice) utterance.voice = preferredVoice;

        utterance.rate = 1.0;
        utterance.pitch = 1.0;

        window.speechSynthesis.speak(utterance);
    }
}
