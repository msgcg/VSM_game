/**
 * Клиентский движок интерактивного симулятора ВСМ «Белый кречет».
 * Обрабатывает таймеры, ветвление диалогов, шкалы лояльности и безопасности.
 */

class VSMSimulator {
    constructor(sessionId, initialTimerSeconds) {
        this.sessionId = sessionId;
        this.timerSeconds = initialTimerSeconds || 25;
        this.timerInterval = null;
        this.isProcessing = false;
        
        this.elements = {
            timerSec: document.getElementById('vsm-timer-sec'),
            timerBox: document.getElementById('vsm-timer-box'),
            dialogueStage: document.getElementById('vsm-dialogue-stage'),
            characterName: document.getElementById('vsm-character-name'),
            characterRole: document.getElementById('vsm-character-role'),
            characterMood: document.getElementById('vsm-character-mood'),
            charAvatar: document.getElementById('vsm-char-avatar'),
            dialogueText: document.getElementById('vsm-dialogue-text'),
            narrativeContext: document.getElementById('vsm-narrative-context'),
            narrativeContextText: document.getElementById('vsm-narrative-context-text'),
            choicesContainer: document.getElementById('vsm-choices-container'),
            aiHintsPanel: document.getElementById('vsm-ai-hints-panel'),
            aiHintReason: document.getElementById('vsm-ai-hint-reason'),
            toast: document.getElementById('vsm-toast'),
            toastMsg: document.getElementById('vsm-toast-msg'),
            
            // Метрики
            valLoyalty: document.getElementById('vsm-val-loyalty'),
            fillLoyalty: document.getElementById('vsm-fill-loyalty'),
            valSafety: document.getElementById('vsm-val-safety'),
            fillSafety: document.getElementById('vsm-fill-safety'),
            valService: document.getElementById('vsm-val-service'),
            fillService: document.getElementById('vsm-fill-service'),
            valStress: document.getElementById('vsm-val-stress'),
            fillStress: document.getElementById('vsm-fill-stress'),
            
            speedo: document.getElementById('vsm-live-speedo'),
            speedoLed: document.getElementById('vsm-live-speedo-led'),

            // Live AI консоль и режимы
            aiStatusPill: document.getElementById('vsm-ai-status-pill'),
            aiStatusText: document.getElementById('vsm-ai-status-text'),
            dialogueHistory: document.getElementById('vsm-dialogue-history'),
            
            // Вкладки
            tabVoice: document.getElementById('vsm-tab-voice'),
            tabText: document.getElementById('vsm-tab-text'),
            tabEquipment: document.getElementById('vsm-tab-equipment'),
            tabChoices: document.getElementById('vsm-tab-choices'),

            // Панели
            paneVoice: document.getElementById('vsm-pane-voice'),
            paneText: document.getElementById('vsm-pane-text'),
            paneEquipment: document.getElementById('vsm-pane-equipment'),
            paneChoices: document.getElementById('vsm-pane-choices'),

            // Элементы голоса и текста
            micBtn: document.getElementById('vsm-mic-btn'),
            micStatus: document.getElementById('vsm-mic-status'),
            micPreview: document.getElementById('vsm-mic-preview'),
            micText: document.getElementById('vsm-mic-text'),
            micSendBar: document.getElementById('vsm-mic-send-bar'),
            userTextInput: document.getElementById('vsm-user-text-input'),
        };

        this.currentMode = 'voice';
        this.isRecording = false;
        this.recordedTranscript = '';
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.speechRecognition = null;
        this.historyData = [];
        this.isSpeaking = false;

        this.init();
    }

    getCleanSpeechText(text) {
        if (!text) return '';
        let s = String(text).trim();
        while (true) {
            let changed = false;
            // Strip speaker prefixes like "Проводник:", "[Проводник]:", "Пассажир:", "Иван:", etc.
            const strippedPrefix = s.replace(/^(?:(?:\[|\()?(?:Проводник|Пассажир|Персонаж|Машинист|Ревизор|Инструктор|Собеседник)(?:\]|\))?[:\-–—]\s*)+/i, '').trim();
            if (strippedPrefix !== s) {
                s = strippedPrefix;
                changed = true;
            }
            if ((s.startsWith('«') && s.endsWith('»')) ||
                (s.startsWith('"') && s.endsWith('"')) ||
                (s.startsWith('“') && s.endsWith('”')) ||
                (s.startsWith('„') && s.endsWith('“')) ||
                (s.startsWith("'") && s.endsWith("'"))) {
                s = s.slice(1, -1).trim();
                changed = true;
            }
            if (/^[«"“„']/.test(s)) {
                s = s.slice(1).trim();
                changed = true;
            }
            if (/[»"”'„]$/.test(s)) {
                s = s.slice(0, -1).trim();
                changed = true;
            }
            if (!changed) break;
        }
        return s;
    }

    formatCleanDialogue(text) {
        const clean = this.getCleanSpeechText(text);
        return clean ? `«${clean}»` : '';
    }

    init() {
        this.defaultTimerSeconds = this.timerSeconds || 30;
        if (this.elements.dialogueText) {
            this.elements.dialogueText.textContent = this.formatCleanDialogue(this.elements.dialogueText.textContent);
        }
        
        // Показываем начальное значение, но таймер НЕ запускаем до окончания речи!
        this.updateTimerDisplay();
        this.bindEvents();
        this.initClock();
        this.updateDynamicTemperature();
        this.initTouchDragAndDrop();
        this.startSpeedometerJitter();
        this.initSpeechRecognition();
        this.updatePassengerVisual(
            this.elements.characterRole?.textContent,
            this.elements.characterName?.textContent,
            this.elements.dialogueText?.textContent,
            this.elements.characterMood?.textContent
        );
        
        // Фоновый эмбиент вагона ВСМ «Белый кречет» на 400 км/ч
        if (window.vsmAudio && window.vsmAudio.startTrainAmbient) {
            window.vsmAudio.startTrainAmbient();
        }

        // Звук отправления/начала шага + автоматическая озвучка пассажира
        if (window.vsmAudio) {
            this.setAiStatus('Воспроизведение реплики пассажира...');
            setTimeout(() => {
                window.vsmAudio.playTrainChime();
                const speech = this.getCleanSpeechText(this.elements.dialogueText?.textContent);
                if (speech && window.vsmAudio.settings && window.vsmAudio.settings.ttsEnabled) {
                    const spType = window.vsmAudio.detectSpeakerType ? 
                        window.vsmAudio.detectSpeakerType(speech, this.elements.characterName?.textContent, this.elements.characterRole?.textContent) : 'male';
                    
                    window.vsmAudio.speak(
                        speech,
                        () => {
                            // Речь началась — таймер на строгой паузе!
                            this.stopTimer();
                            this.setAiStatus('Воспроизведение реплики...');
                        },
                        () => {
                            // Речь окончена — таймер стартует для решения проводника!
                            this.setAiStatus('Ваша очередь: примите решение или ответьте в эфир');
                            this.startTimer(this.defaultTimerSeconds);
                        },
                        spType
                    );
                } else {
                    // Если TTS отключен — даем 1 сек на чтение и запускаем таймер
                    setTimeout(() => {
                        this.setAiStatus('Ваша очередь: примите решение или ответьте в эфир');
                        this.startTimer(this.defaultTimerSeconds);
                    }, 1000);
                }
            }, 300);
        } else {
            this.startTimer(this.defaultTimerSeconds);
        }
    }

    bindEvents() {
        // Поддержка цифровых клавиш 1..9 для мгновенного выбора
        document.addEventListener('keydown', (e) => {
            if (this.isProcessing) return;
            if (e.target && ['INPUT', 'TEXTAREA'].includes(e.target.tagName)) return;
            const key = parseInt(e.key, 10);
            if (!isNaN(key) && key >= 1 && key <= 9) {
                const choiceBtns = document.querySelectorAll('.vsm-choice-btn');
                if (choiceBtns && choiceBtns[key - 1]) {
                    choiceBtns[key - 1].click();
                }
            }
        });

        // Редактирование распознанной речи проводника перед отправкой
        if (this.elements.micText) {
            this.elements.micText.addEventListener('input', (e) => {
                this.stopTimer();
                this.recordedTranscript = e.target.value;
                if (this.elements.userTextInput) {
                    this.elements.userTextInput.value = e.target.value;
                }
            });
            this.elements.micText.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendRecordedVoice();
                } else if (e.key === 'Escape') {
                    e.preventDefault();
                    this.cancelVoiceRecording();
                }
            });
        }

        if (this.elements.userTextInput) {
            this.elements.userTextInput.addEventListener('focus', () => {
                if (!this.isProcessing) this.stopTimer();
            });
            this.elements.userTextInput.addEventListener('input', (e) => {
                if (!this.isProcessing) this.stopTimer();
                if (this.elements.micText && 'value' in this.elements.micText) {
                    this.elements.micText.value = e.target.value;
                }
            });
        }
    }

    startTimer(seconds) {
        clearInterval(this.timerInterval);
        this.timerSeconds = seconds;
        this.updateTimerDisplay();

        if (seconds <= 0) return;

        this.timerInterval = setInterval(() => {
            this.timerSeconds--;
            this.updateTimerDisplay();

            if (this.timerSeconds <= 5 && this.timerSeconds > 0) {
                if (window.vsmAudio) {
                    window.vsmAudio.playWarning();
                }
            }

            if (this.timerSeconds <= 0) {
                clearInterval(this.timerInterval);
                this.handleTimeout();
            }
        }, 1000);
    }

    updateTimerDisplay() {
        if (!this.elements.timerSec) return;
        this.elements.timerSec.textContent = this.timerSeconds;

        if (this.timerSeconds <= 6) {
            this.elements.timerBox?.classList.add('danger');
        } else {
            this.elements.timerBox?.classList.remove('danger');
        }
    }

    stopTimer() {
        clearInterval(this.timerInterval);
        this.timerInterval = null;
    }

    setAiStatus(text) {
        if (this.elements.aiStatusText) {
            this.elements.aiStatusText.textContent = text;
        }
    }

    switchMode(mode) {
        this.currentMode = mode;
        const tabs = {
            voice: this.elements.tabVoice,
            text: this.elements.tabText,
            equipment: this.elements.tabEquipment,
            choices: this.elements.tabChoices,
        };
        const panes = {
            voice: this.elements.paneVoice,
            text: this.elements.paneText,
            equipment: this.elements.paneEquipment,
            choices: this.elements.paneChoices,
        };

        Object.keys(tabs).forEach(k => {
            if (tabs[k]) {
                if (k === mode) tabs[k].classList.add('active');
                else tabs[k].classList.remove('active');
            }
        });

        Object.keys(panes).forEach(k => {
            if (panes[k]) {
                panes[k].style.display = (k === mode) ? (k === 'voice' ? 'flex' : 'block') : 'none';
            }
        });

        if (mode === 'text' && this.elements.userTextInput) {
            setTimeout(() => this.elements.userTextInput.focus(), 100);
        }
    }

    initSpeechRecognition() {
        const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (SpeechRec) {
            try {
                this.speechRecognition = new SpeechRec();
                this.speechRecognition.lang = 'ru-RU';
                this.speechRecognition.interimResults = true;
                this.speechRecognition.continuous = true;

                this.speechRecognition.onresult = (event) => {
                    let interim = '';
                    let final = '';
                    for (let i = event.resultIndex; i < event.results.length; ++i) {
                        if (event.results[i].isFinal) {
                            final += event.results[i][0].transcript;
                        } else {
                            interim += event.results[i][0].transcript;
                        }
                    }
                    const recognized = final || interim;
                    if (recognized && recognized.trim()) {
                        this.recordedTranscript = recognized.trim();
                        if (this.elements.micText) {
                            if ('value' in this.elements.micText) {
                                this.elements.micText.value = this.recordedTranscript;
                            } else {
                                this.elements.micText.textContent = `«${this.recordedTranscript}»`;
                            }
                        }
                    }
                };

                this.speechRecognition.onerror = (e) => {
                    console.warn('Speech recognition warning:', e.error);
                };
            } catch (err) {
                console.warn('Speech recognition init error:', err);
            }
        }
    }

    async toggleVoiceRecording() {
        if (this.isProcessing) return;

        if (!this.isRecording) {
            // Начало записи
            this.stopTimer(); // ТАЙМЕР НА СТРОГОЙ ПАУЗЕ во время речи проводника!
            this.recordedTranscript = '';

            // Проверка поддержки getUserMedia
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                this.showToast('Микрофон не поддерживается этим браузером. Используйте текстовый ввод.', 'warning');
                return;
            }

            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                this.micStream = stream;
                this.isRecording = true;

                if (this.elements.micBtn) this.elements.micBtn.classList.add('recording');
                if (this.elements.micStatus) this.elements.micStatus.textContent = 'Идет радиопередача... Говорите в микрофон!';
                if (this.elements.micPreview) this.elements.micPreview.style.display = 'flex';
                if (this.elements.micText) {
                    if ('value' in this.elements.micText) this.elements.micText.value = '';
                    else this.elements.micText.textContent = 'Слушаю вас...';
                }
                if (this.elements.micSendBar) this.elements.micSendBar.style.display = 'none';

                // Запуск визуализатора частот речи
                this.startMicVisualizer(stream);

                // Запуск браузерного распознавания речи Web Speech API для мгновенного отображения текста
                if (this.speechRecognition) {
                    try { this.speechRecognition.start(); } catch (e) {}
                }

                // Запуск MediaRecorder для отправки в бортовой ASR
                this.audioChunks = [];
                try {
                    const mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus' : (MediaRecorder.isTypeSupported('audio/ogg;codecs=opus') ? 'audio/ogg;codecs=opus' : '');
                    this.mediaRecorder = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream);
                    this.mediaRecorder.ondataavailable = (e) => {
                        if (e.data && e.data.size > 0) this.audioChunks.push(e.data);
                    };
                    this.mediaRecorder.start();
                } catch (recErr) {
                    console.warn('MediaRecorder init error:', recErr);
                }

            } catch (err) {
                console.error('Microphone access denied or error:', err);
                this.isRecording = false;
                if (this.elements.micBtn) this.elements.micBtn.classList.remove('recording');
                if (this.elements.micStatus) this.elements.micStatus.textContent = 'Доступ к микрофону отклонен. Разрешите микрофон в браузере или используйте текстовый ввод.';
                this.showToast('Разрешите доступ к микрофону в браузере для голосовой связи', 'danger');
                this.startTimer(this.defaultTimerSeconds || 25);
            }
        } else {
            // Остановка записи
            this.isRecording = false;
            this.stopMicVisualizer();
            if (this.elements.micBtn) this.elements.micBtn.classList.remove('recording');
            if (this.elements.micStatus) this.elements.micStatus.textContent = 'Обработка радиосигнала связи...';

            if (this.speechRecognition) {
                try { this.speechRecognition.stop(); } catch (e) {}
            }

            if (this.micStream) {
                this.micStream.getTracks().forEach(track => track.stop());
                this.micStream = null;
            }

            if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
                this.mediaRecorder.stop();
                this.mediaRecorder.onstop = async () => {
                    // Отправляем аудио на бортовой модуль распознавания речи с Vulkan-ускорением
                    const mimeType = this.mediaRecorder.mimeType || 'audio/webm;codecs=opus';
                    const audioBlob = new Blob(this.audioChunks, { type: mimeType });
                    if (this.elements.micStatus) {
                        this.elements.micStatus.textContent = 'Распознавание речи...';
                    }

                    try {
                        const res = await fetch('/api/v1/live/asr/', {
                            method: 'POST',
                            headers: { 'Content-Type': mimeType },
                            body: audioBlob
                        });
                        const data = await res.json();
                        let finalSpeech = (data && data.ok && data.text) ? data.text.trim() : '';

                        // Если бортовой модуль не уловил речь, но браузер что-то успел записать
                        if (!finalSpeech && this.recordedTranscript && this.recordedTranscript.length > 2 && this.recordedTranscript !== 'Слушаю вас...') {
                            finalSpeech = this.recordedTranscript.trim();
                        }

                        if (finalSpeech && finalSpeech !== 'Слушаю вас...') {
                            this.showRecognizedSpeechForEditing(finalSpeech);
                        } else {
                            if (this.elements.micStatus) this.elements.micStatus.textContent = 'Речь не расслышана. Нажмите на микрофон еще раз или введите текст.';
                            if (this.elements.micSendBar) this.elements.micSendBar.style.display = 'none';
                            if (this.elements.micPreview) this.elements.micPreview.style.display = 'none';
                            this.startTimer(this.timerSeconds || this.defaultTimerSeconds || 25);
                        }
                    } catch (e) {
                        if (this.recordedTranscript && this.recordedTranscript.length > 2 && this.recordedTranscript !== 'Слушаю вас...') {
                            this.showRecognizedSpeechForEditing(this.recordedTranscript);
                        } else {
                            if (this.elements.micStatus) this.elements.micStatus.textContent = 'Нажмите еще раз или воспользуйтесь текстовым вводом.';
                            if (this.elements.micSendBar) this.elements.micSendBar.style.display = 'none';
                            if (this.elements.micPreview) this.elements.micPreview.style.display = 'none';
                            this.startTimer(this.timerSeconds || this.defaultTimerSeconds || 25);
                        }
                    }
                };
            } else if (this.recordedTranscript && this.recordedTranscript.length > 2 && this.recordedTranscript !== 'Слушаю вас...') {
                this.showRecognizedSpeechForEditing(this.recordedTranscript);
            } else {
                if (this.elements.micStatus) this.elements.micStatus.textContent = 'Речь не услышана. Нажмите на микрофон и четко произнесите реплику.';
                if (this.elements.micSendBar) this.elements.micSendBar.style.display = 'none';
                if (this.elements.micPreview) this.elements.micPreview.style.display = 'none';
                this.startTimer(this.timerSeconds || this.defaultTimerSeconds || 25);
            }
        }
    }

    onTextInputChange() {
        const sendBtn = document.getElementById('vsm-text-send-btn');
        const input = this.elements.userTextInput;
        if (!sendBtn || !input) return;
        if (input.value && input.value.trim().length > 0) {
            sendBtn.style.display = 'inline-flex';
        } else {
            sendBtn.style.display = 'none';
        }
    }

    showRecognizedSpeechForEditing(text) {
        this.recordedTranscript = text;
        if (this.elements.userTextInput) {
            this.elements.userTextInput.value = text;
            this.onTextInputChange();
        }
        if (this.elements.micStatus) {
            this.elements.micStatus.textContent = 'Речь распознана. Отредактируйте или нажмите «Сказать»';
        }

        setTimeout(() => {
            if (this.elements.userTextInput) {
                this.elements.userTextInput.focus();
                if (typeof this.elements.userTextInput.setSelectionRange === 'function') {
                    const len = this.elements.userTextInput.value.length;
                    this.elements.userTextInput.setSelectionRange(len, len);
                }
            }
        }, 50);

        this.stopTimer();
    }

    startMicVisualizer(stream) {
        const canvas = document.getElementById('vsm-mic-canvas');
        if (!canvas) return;
        try {
            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            if (!AudioCtx) return;
            this.visCtx = new AudioCtx();
            const source = this.visCtx.createMediaStreamSource(stream);
            this.analyser = this.visCtx.createAnalyser();
            this.analyser.fftSize = 64;
            source.connect(this.analyser);

            const bufferLength = this.analyser.frequencyBinCount;
            const dataArray = new Uint8Array(bufferLength);
            const ctx2d = canvas.getContext('2d');
            canvas.style.display = 'block';

            const draw = () => {
                if (!this.isRecording) return;
                this.visAnimId = requestAnimationFrame(draw);
                this.analyser.getByteFrequencyData(dataArray);

                ctx2d.clearRect(0, 0, canvas.width, canvas.height);
                const barWidth = (canvas.width / bufferLength) * 1.5;
                let x = 0;
                for (let i = 0; i < bufferLength; i++) {
                    const barHeight = (dataArray[i] / 255) * canvas.height * 0.9;
                    const gradient = ctx2d.createLinearGradient(0, canvas.height, 0, 0);
                    gradient.addColorStop(0, '#00d2ff');
                    gradient.addColorStop(1, '#22c55e');
                    ctx2d.fillStyle = gradient;
                    ctx2d.fillRect(x, canvas.height - barHeight, barWidth - 2, barHeight);
                    x += barWidth;
                }
            };
            draw();
        } catch (e) {
            console.warn('Mic visualizer error:', e);
        }
    }

    stopMicVisualizer() {
        if (this.visAnimId) {
            cancelAnimationFrame(this.visAnimId);
            this.visAnimId = null;
        }
        if (this.visCtx) {
            try { this.visCtx.close(); } catch (_) {}
            this.visCtx = null;
        }
        const canvas = document.getElementById('vsm-mic-canvas');
        if (canvas) {
            const ctx2d = canvas.getContext('2d');
            ctx2d.clearRect(0, 0, canvas.width, canvas.height);
            canvas.style.display = 'none';
        }
    }

    handleDragStart(e, code, title) {
        e.dataTransfer.setData('text/plain', JSON.stringify({ code, title }));
        e.dataTransfer.effectAllowed = 'copyMove';
        const dropzones = document.querySelectorAll('.vsm-car-dropzone, #vsm-dialogue-stage, #card-dialogue-wrap, #vsm-car-drop-target');
        dropzones.forEach(dz => dz.classList.add('highlight-target'));
    }

    handleDragEnd(e) {
        const dropzones = document.querySelectorAll('.vsm-car-dropzone, #vsm-dialogue-stage, #card-dialogue-wrap, #vsm-car-drop-target');
        dropzones.forEach(dz => {
            dz.classList.remove('highlight-target');
            dz.classList.remove('drag-active');
        });
    }

    handleDragOver(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'copy';
        e.currentTarget.classList.add('drag-active');
    }

    handleDragLeave(e) {
        e.currentTarget.classList.remove('drag-active');
    }

    handleDrop(e) {
        e.preventDefault();
        e.currentTarget.classList.remove('drag-active');
        const dropzones = document.querySelectorAll('.vsm-car-dropzone, #vsm-dialogue-stage, #card-dialogue-wrap, #vsm-car-drop-target');
        dropzones.forEach(dz => dz.classList.remove('highlight-target'));

        try {
            const raw = e.dataTransfer.getData('text/plain');
            if (raw) {
                const data = JSON.parse(raw);
                if (data && data.code) {
                    this.useEquipment(data.code, data.title || 'Оборудование вагона');
                }
            }
        } catch (err) {
            console.warn('Drop error:', err);
        }
    }

    initClock() {
        const update = () => {
            const clockEl = document.getElementById('vsm-car-clock');
            if (clockEl) {
                const now = new Date();
                const hh = String(now.getHours()).padStart(2, '0');
                const mm = String(now.getMinutes()).padStart(2, '0');
                clockEl.textContent = `${hh}:${mm}`;
            }
        };
        update();
        setInterval(update, 1000);
    }

    updateDynamicTemperature(overrideTemp = null) {
        const tempEl = document.getElementById('vsm-car-temp');
        if (!tempEl) return;

        if (overrideTemp) {
            tempEl.textContent = `САЛОН: ${overrideTemp}`;
            tempEl.className = 'vsm-temp-normal';
            return;
        }

        const sceneText = [
            document.title,
            this.elements.dialogueText?.textContent || '',
            document.querySelector('.vsm-case-descr')?.textContent || '',
            document.querySelector('.vsm-scene-title')?.textContent || ''
        ].join(' ').toLowerCase();

        tempEl.classList.remove('vsm-temp-fire', 'vsm-temp-overheat', 'vsm-temp-warning', 'vsm-temp-cold', 'vsm-temp-normal');

        if (sceneText.includes('пожар') || sceneText.includes('задымлен') || sceneText.includes('огн') || sceneText.includes('горит') || sceneText.includes('пламя')) {
            tempEl.textContent = 'САЛОН: +41°C';
            tempEl.classList.add('vsm-temp-fire');
        } else if (sceneText.includes('жар') || sceneText.includes('душн') || sceneText.includes('кондиционер') || sceneText.includes('климат') || sceneText.includes('перегрев') || sceneText.includes('+33') || sceneText.includes('+30')) {
            tempEl.textContent = 'САЛОН: +31°C';
            tempEl.classList.add('vsm-temp-overheat');
        } else if (sceneText.includes('скнб') || sceneText.includes('букс') || sceneText.includes('нагрев букс')) {
            tempEl.textContent = 'САЛОН: +27°C';
            tempEl.classList.add('vsm-temp-warning');
        } else if (sceneText.includes('холод') || sceneText.includes('мороз') || sceneText.includes('замерз') || sceneText.includes('сквозняк') || sceneText.includes('дует') || sceneText.includes('открыт')) {
            tempEl.textContent = 'САЛОН: +16°C';
            tempEl.classList.add('vsm-temp-cold');
        } else {
            tempEl.textContent = 'САЛОН: +22°C';
            tempEl.classList.add('vsm-temp-normal');
        }
    }

    initTouchDragAndDrop() {
        const items = document.querySelectorAll('.vsm-tactile-item');
        const dropTarget = document.getElementById('vsm-car-drop-target') || document.querySelector('.vsm-car-dropzone');
        if (!items.length || !dropTarget) return;

        items.forEach(item => {
            let startX = 0, startY = 0;
            let isDragging = false;
            let avatar = null;
            const actionCode = item.getAttribute('data-code') || '';
            const actionTitle = item.getAttribute('data-title') || item.getAttribute('title') || 'Оборудование вагона';

            item.addEventListener('touchstart', (e) => {
                if (e.touches.length !== 1) return;
                startX = e.touches[0].clientX;
                startY = e.touches[0].clientY;
                isDragging = false;
            }, { passive: true });

            item.addEventListener('touchmove', (e) => {
                if (e.touches.length !== 1) return;
                const touch = e.touches[0];
                const dx = touch.clientX - startX;
                const dy = touch.clientY - startY;

                if (!isDragging && Math.hypot(dx, dy) > 10) {
                    isDragging = true;
                    dropTarget.classList.add('highlight-target');

                    avatar = document.createElement('div');
                    avatar.className = 'vsm-touch-drag-avatar';
                    avatar.innerHTML = item.innerHTML;
                    document.body.appendChild(avatar);
                }

                if (isDragging && avatar) {
                    if (e.cancelable) e.preventDefault();
                    avatar.style.left = touch.clientX + 'px';
                    avatar.style.top = touch.clientY + 'px';

                    const rect = dropTarget.getBoundingClientRect();
                    const isOver = (
                        touch.clientX >= rect.left &&
                        touch.clientX <= rect.right &&
                        touch.clientY >= rect.top &&
                        touch.clientY <= rect.bottom
                    );

                    if (isOver) {
                        dropTarget.classList.add('drag-active');
                    } else {
                        dropTarget.classList.remove('drag-active');
                    }
                }
            }, { passive: false });

            const cleanUp = () => {
                if (avatar && avatar.parentNode) {
                    avatar.parentNode.removeChild(avatar);
                }
                avatar = null;
                dropTarget.classList.remove('highlight-target', 'drag-active');
                isDragging = false;
            };

            item.addEventListener('touchend', (e) => {
                if (isDragging) {
                    const touch = e.changedTouches[0];
                    const rect = dropTarget.getBoundingClientRect();
                    const isOver = (
                        touch.clientX >= rect.left &&
                        touch.clientX <= rect.right &&
                        touch.clientY >= rect.top &&
                        touch.clientY <= rect.bottom
                    );

                    cleanUp();

                    if (isOver && actionCode) {
                        this.useEquipment(actionCode, actionTitle);
                    }
                } else {
                    cleanUp();
                }
            });

            item.addEventListener('touchcancel', cleanUp);
        });
    }

    sendRecordedVoice() {
        this.sendTextTurn();
    }

    cancelVoiceRecording() {
        this.isRecording = false;
        this.stopMicVisualizer();
        if (this.elements.micBtn) this.elements.micBtn.classList.remove('recording');
        if (this.elements.micStatus) this.elements.micStatus.textContent = 'Нажмите на микрофон для ответа голосом';
        this.startTimer(this.timerSeconds || this.defaultTimerSeconds || 25);
    }

    sendTextTurn(e) {
        if (e) e.preventDefault();
        const input = this.elements.userTextInput;
        if (!input) return;
        const text = input.value.trim();
        if (!text) {
            this.showToast('Введите слова проводника перед отправкой', 'warning');
            return;
        }
        input.value = '';
        this.onTextInputChange();
        if (this.elements.micStatus) this.elements.micStatus.textContent = 'Нажмите и говорите';
        this.sendLiveTurn(text, '');
    }

    useEquipment(actionCode, actionTitle) {
        if (this.isProcessing) return;
        
        // Звуковой отклик применения оборудования
        if (window.vsmAudio) {
            if (actionCode === 'emergency_brake') window.vsmAudio.playEmergency();
            else if (actionCode === 'driver_intercom') window.vsmAudio.playMachinistRadioChirp();
            else if (actionCode === 'electric_panel') window.vsmAudio.playSystemTelemetryBeep();
            else window.vsmAudio.playClick();
        }

        // Динамическая реакция температуры на климат и огнетушитель
        if (actionCode === 'electric_panel' || actionCode === 'fire_extinguisher') {
            this.updateDynamicTemperature('+22°C');
        }

        const input = this.elements.userTextInput;
        const typedText = input ? input.value.trim() : '';
        const speechText = typedText || `Применяю [${actionTitle}] по регламенту вагона.`;
        if (input) {
            input.value = '';
            this.onTextInputChange();
        }

        this.showToast(`Действие экипажа: [${actionTitle}]`, 'info');
        this.sendLiveTurn(speechText, actionCode, actionTitle);
    }

    async sendLiveTurn(message, action, actionTitle = '') {
        if (this.isProcessing) return;
        this.isProcessing = true;
        this.stopTimer(); // ТАЙМЕР НА СТРОГОЙ ПАУЗЕ во время обращения к ИИ и озвучки!

        this.setAiStatus('Нейросетевой ассистент анализирует действия экипажа...');
        this.showToast('Передача доклада в систему поезда...', 'info');

        // Добавляем реплику/действие проводника в ленту
        this.appendHistoryTurn('conductor', message, action, '', 'formal', actionTitle);

        // Готовим запрос
        const payload = {
            session_id: this.sessionId,
            message: message,
            action: action,
            history: this.historyData.slice(-6)
        };

        try {
            const res = await fetch('/api/v1/live/turn/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(payload)
            });

            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const json = await res.json();
            this.isProcessing = false;

            if (json && json.ok && json.data) {
                const turn = json.data;
                this.handleLiveTurnResponse(turn);
            } else {
                this.showToast('Ошибка обработки ответа ИИ', 'danger');
                this.startTimer(this.defaultTimerSeconds || 25);
            }
        } catch (err) {
            this.isProcessing = false;
            console.error('sendLiveTurn error:', err);
            this.showToast('Сетевой сбой. Повторите попытку.', 'danger');
            this.setAiStatus('Повторите попытку ответа');
            this.startTimer(this.defaultTimerSeconds || 25);
        }
    }

    handleLiveTurnResponse(turn) {
        const reply = turn.character_reply || '';
        const mood = turn.character_mood || 'formal';
        const eventText = turn.system_event || '';
        const feedback = turn.feedback || '';
        const status = turn.session_status || turn.status || 'in_progress';

        // Обновляем метрики
        if (turn.current_loyalty !== undefined) {
            this.updateLiveMetric('loyalty', turn.current_loyalty);
        }
        if (turn.current_safety !== undefined) {
            this.updateLiveMetric('safety', turn.current_safety);
        }
        if (turn.current_service !== undefined) {
            this.updateLiveMetric('service', turn.current_service);
        }
        if (turn.current_stress !== undefined) {
            this.updateLiveMetric('stress', turn.current_stress);
        }

        // Обновляем скорость если изменилась
        const deltas = turn.vitals_delta || {};
        if (deltas.train_speed !== undefined) {
            this.updateSpeed(deltas.train_speed);
        }

        const cleanReply = this.getCleanSpeechText(reply);

        // Добавляем реплику персонажа в объединенную ленту диалога
        this.appendHistoryTurn('character', cleanReply, '', eventText, mood);

        // Обновляем главный текст только если лента чата отсутствует (фолбэк)
        const chatFeedEl = document.getElementById('vsm-chat-feed');
        if (!chatFeedEl && this.elements.dialogueText) {
            this.elements.dialogueText.textContent = this.formatCleanDialogue(cleanReply);
        }

        if (this.elements.narrativeContext && eventText) {
            this.elements.narrativeContext.style.display = 'flex';
            if (this.elements.narrativeContextText) {
                this.elements.narrativeContextText.textContent = eventText;
            }
        }

        // Обновляем визуал персонажа и настроение
        this.updatePassengerVisual(
            this.elements.characterRole?.textContent,
            this.elements.characterName?.textContent,
            cleanReply,
            mood
        );

        if (feedback) {
            this.showToast(feedback, 'info');
        }

        // Проверяем финал смены (Function Calling / вердикт ИИ)
        if (status === 'completed') {
            if (window.vsmAudio) window.vsmAudio.playSuccess();
            this.setAiStatus('Смена успешно принята по стандартам ВСМ!');
            this.showSuccessModal({
                title: 'Смена успешно принята • Стандарт ВСМ соблюден',
                character_reply: cleanReply,
                feedback: feedback || 'Ситуация полностью урегулирована в строгом соответствии со стандартами ВСМ «Белый кречет».',
                score: turn.score || 95,
                earned_xp: turn.earned_xp || 45,
                result_url: `/simulation/${this.sessionId}/result/`
            });
            return;
        } else if (status === 'failed') {
            if (window.vsmAudio) window.vsmAudio.playEmergency();
            this.setAiStatus('Допущено нарушение регламентов ВСМ!');
            this.showFailureModal({
                error_title: 'Сбой рейса ВСМ',
                title: 'Сценарий провален',
                action_taken: this.lastConductorTurnText || 'Действия экипажа привели к критическому нарушению',
                user_action: this.lastConductorTurnText || 'Действия экипажа привели к критическому нарушению',
                expert_comment: feedback || 'Нарушены требования регламентов и стандартов ВСМ.',
                resolution_report: feedback || 'Нарушены требования регламентов и стандартов ВСМ.',
                regulation_reference: 'СТО ВСМ 03.011/013-2026 • Правила безопасности движения',
                recommended_approach: 'Соблюдайте 4-шаговый протокол ВСМ и правила применения оборудования вагона.',
                correct_solution: 'Соблюдайте 4-шаговый протокол ВСМ и правила применения оборудования вагона.',
                result_url: `/simulation/${this.sessionId}/result/`
            });
            return;
        }

        // Обработка подсказок и вариантов действий от ИИ (offer_hints)
        if (turn.show_hints) {
            this.showHintsPanel(turn.hint_reason, turn.suggested_actions);
        } else {
            this.hideHintsPanel();
        }

        // Озвучка ответа персонажа через бортовой комплекс TTS
        if (cleanReply && window.vsmAudio && window.vsmAudio.settings && window.vsmAudio.settings.ttsEnabled) {
            const spType = window.vsmAudio.detectSpeakerType ? 
                window.vsmAudio.detectSpeakerType(cleanReply, this.elements.characterName?.textContent, this.elements.characterRole?.textContent) : 'male';

            this.setAiStatus('Воспроизведение реплики...');
            window.vsmAudio.speak(
                cleanReply,
                () => {
                    this.stopTimer(); // Строгая пауза во время речи!
                    this.setAiStatus('Воспроизведение реплики...');
                },
                () => {
                    // Речь окончена — таймер стартует!
                    this.setAiStatus('Примите следующее решение или ответьте в эфир');
                    this.startTimer(this.defaultTimerSeconds || 30);
                },
                spType
            );
        } else {
            // Если звук выключен — даем 1.5 секунды на чтение реплики и запускаем таймер
            setTimeout(() => {
                this.setAiStatus('Примите следующее решение или ответьте в эфир');
                this.startTimer(this.defaultTimerSeconds || 30);
            }, 1200);
        }
    }

    showHintsPanel(reason, suggestedActions) {
        const panel = this.elements.aiHintsPanel || document.getElementById('vsm-ai-hints-panel');
        if (!panel) return;

        const reasonEl = this.elements.aiHintReason || document.getElementById('vsm-ai-hint-reason');
        if (reasonEl && reason) {
            reasonEl.textContent = reason;
        }

        const container = this.elements.choicesContainer || document.getElementById('vsm-choices-container');
        if (container && Array.isArray(suggestedActions) && suggestedActions.length > 0) {
            container.innerHTML = '';
            suggestedActions.forEach((act, idx) => {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'vsm-choice-btn';
                btn.style.padding = '0.85rem 1rem';
                btn.onclick = () => {
                    if (this.elements.userTextInput) {
                        this.elements.userTextInput.value = act.text;
                    }
                    this.sendLiveTurn(act.text, '');
                    this.hideHintsPanel();
                };

                const numDiv = document.createElement('div');
                numDiv.className = 'vsm-choice-num';
                numDiv.textContent = (idx + 1).toString();

                const contentDiv = document.createElement('div');
                contentDiv.className = 'vsm-choice-content';

                const titleDiv = document.createElement('div');
                titleDiv.className = 'vsm-choice-title';
                titleDiv.style.fontSize = '0.85rem';
                titleDiv.textContent = act.text || '';
                contentDiv.appendChild(titleDiv);

                if (act.hint) {
                    const hintDiv = document.createElement('div');
                    hintDiv.className = 'vsm-choice-hint';
                    hintDiv.style.fontSize = '0.74rem';
                    hintDiv.textContent = act.hint;
                    contentDiv.appendChild(hintDiv);
                }

                btn.appendChild(numDiv);
                btn.appendChild(contentDiv);
                container.appendChild(btn);
            });
        }

        panel.style.display = 'block';
        if (window.vsmAudio && window.vsmAudio.playSystemTelemetryBeep) {
            window.vsmAudio.playSystemTelemetryBeep();
        }
        this.showToast('ИИ-наставник ВСМ предоставил варианты действий', 'info');
    }

    hideHintsPanel() {
        const panel = this.elements.aiHintsPanel || document.getElementById('vsm-ai-hints-panel');
        if (panel) {
            panel.style.display = 'none';
        }
    }

    requestHint() {
        if (this.isProcessing) return;
        this.showToast('Запрос тактической подсказки у ИИ-наставника...', 'info');
        this.sendLiveTurn('Подскажите, как правильно поступить по стандарту ВСМ в этой ситуации?', '');
    }

    updateLiveMetric(name, value) {
        const key = name.charAt(0).toUpperCase() + name.slice(1);
        const valEl = this.elements[`val${key}`];
        const fillEl = this.elements[`fill${key}`];
        if (valEl) valEl.textContent = `${value}%`;
        if (fillEl) fillEl.style.width = `${value}%`;
    }

    getMoodBadge(mood, text = '') {
        const moodLower = (mood || '').toLowerCase();
        const fullText = (text || '').toLowerCase();
        let cls = 'vsm-mood-default';
        let label = mood || 'В диалоге';

        if (moodLower.includes('спокойн') || moodLower.includes('делов') || moodLower.includes('формальн') || moodLower.includes('formal') || moodLower.includes('calm')) {
            cls = 'vsm-mood-default';
            label = 'Деловой тон';
        } else if (moodLower.includes('благод') || moodLower.includes('grateful')) {
            cls = 'vsm-mood-default';
            label = 'Благодарен';
        } else if (moodLower.includes('систем') || moodLower.includes('system')) {
            cls = 'vsm-mood-system';
            label = 'Телеметрия';
        } else if (moodLower.includes('агресс') || moodLower.includes('раздраж') || moodLower.includes('гнев') || 
                   moodLower.includes('критическ') || moodLower.includes('irritated') || fullText.includes('сердц') || fullText.includes('инфаркт')) {
            cls = 'vsm-mood-danger';
            label = 'Раздражен';
        } else if (moodLower.includes('паник') || moodLower.includes('тревож') || moodLower.includes('беспокой') || moodLower.includes('испуг') || moodLower.includes('panicked')) {
            cls = 'vsm-mood-warning';
            label = 'В панике';
        }
        return { cls, label };
    }

    getActionTitle(action) {
        const titles = {
            'emergency_brake': 'Срыв стоп-крана',
            'fire_extinguisher': 'Применение огнетушителя ОВП-8',
            'electric_panel': 'Осмотр электрощита и СКНБ',
            'aed_medkit': 'Вскрытие аптечки и АНД',
            'ukeb_scan': 'Проверка по терминалу УКЭБ',
            'tea_service': 'Предложить чай / воду с лимоном',
            'driver_intercom': 'Связь с машинистом по УПС',
            'glass_hammer': 'Взять аварийный молоток'
        };
        return titles[action] || action;
    }

    appendHistoryTurn(role, text, action = '', systemEvent = '', mood = 'formal', actionTitle = '') {
        const displayActionTitle = actionTitle || this.getActionTitle(action);
        if (role === 'conductor') {
            const actLabel = displayActionTitle ? `[${displayActionTitle}] ` : (action ? `[${action}] ` : '');
            this.lastConductorTurnText = `${actLabel}${text}`.trim();
            this.historyData.push({ role: 'user', content: this.lastConductorTurnText });
        } else {
            this.historyData.push({ role: 'assistant', content: text });
        }

        const feed = document.getElementById('vsm-chat-feed');
        if (!feed) {
            // Фолбэк для обратной совместимости
            if (this.elements.dialogueHistory) {
                this.elements.dialogueHistory.style.display = 'flex';
                const turnDiv = document.createElement('div');
                turnDiv.className = `vsm-history-turn ${role}`;
                if (role === 'conductor') {
                    const actBadge = displayActionTitle ? `<span style="display: inline-block; background: rgba(0, 210, 255, 0.25); border: 1px solid rgba(0, 210, 255, 0.5); padding: 0.15rem 0.5rem; border-radius: 6px; font-size: 0.74rem; font-weight: 800; color: #7dd3fc; margin-right: 0.4rem;">[${displayActionTitle}]</span>` : '';
                    turnDiv.innerHTML = `<div class="vsm-history-bubble"><div style="font-size: 0.72rem; font-weight: 800; color: #7dd3fc; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.25rem;">Экипаж ВСМ</div>${actBadge}${text || `Действие с оборудованием: [${displayActionTitle}]`}</div>`;
                } else {
                    const evBadge = systemEvent ? `<div style="font-size: 0.75rem; color: var(--vsm-cyan); margin-top: 0.35rem; display: flex; align-items: center; gap: 0.35rem;"><i data-lucide="info" style="width: 14px; height: 14px; flex-shrink: 0;"></i><span>${systemEvent}</span></div>` : '';
                    turnDiv.innerHTML = `<div class="vsm-history-bubble"><div style="font-size: 0.72rem; font-weight: 800; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.25rem;">${this.elements.characterName?.textContent || 'Пассажир'}</div>${text}${evBadge}</div>`;
                }
                this.elements.dialogueHistory.appendChild(turnDiv);
                this.elements.dialogueHistory.scrollTop = this.elements.dialogueHistory.scrollHeight;
                if (window.lucide) lucide.createIcons();
            }
            return;
        }

        const isConductor = (role === 'conductor');
        const rowDiv = document.createElement('div');
        rowDiv.className = `vsm-chat-row ${isConductor ? 'conductor' : 'passenger'}`;

        if (isConductor) {
            const actBadge = displayActionTitle ? `<div class="vsm-action-badge"><i data-lucide="wrench" style="width: 14px; height: 14px;"></i><span>Действие: [${displayActionTitle}]</span></div>` : '';
            const safeText = this.formatCleanDialogue(text || (displayActionTitle ? `Применяю [${displayActionTitle}] по регламенту вагона.` : ''));
            const textHtml = safeText ? `<div class="vsm-speech-text conductor-text" style="color: #f1f5f9; font-size: 1.05rem;">${safeText}</div>` : '';
            const conductorAvatar = window.VSM_CONDUCTOR_AVATAR || (feed ? feed.dataset.conductorAvatar : '') || '/static/simulator/img/avatar_1.svg';

            rowDiv.innerHTML = `
                <div class="vsm-conductor-frame-col">
                    <div class="vsm-conductor-avatar-box">
                        <img src="${conductorAvatar}" alt="Проводник ВСМ" class="vsm-conductor-avatar-img">
                    </div>
                    <div class="vsm-conductor-role-pill" title="Экипаж поезда">
                        <span class="vsm-status-indicator-dot conductor-dot"></span>
                        <span>Экипаж ВСМ</span>
                    </div>
                </div>
                <div class="vsm-speech-bubble vsm-speech-bubble-conductor">
                    <div class="vsm-speech-header">
                        <div class="vsm-speech-speaker">
                            <span class="vsm-speaker-name" style="color: #38bdf8;">Экипаж ВСМ (Вы)</span>
                            <span class="vsm-mood-badge vsm-mood-conductor">В радиоэфире</span>
                        </div>
                        <div class="vsm-speech-time-badge">
                            <i data-lucide="radio" style="width: 13px; height: 13px;"></i>
                            <span>Доклад</span>
                        </div>
                    </div>
                    ${textHtml}
                    ${actBadge}
                </div>
            `;
        } else {
            const currentAvatar = this.elements.characterAvatar ? this.elements.characterAvatar.src : '/static/simulator/img/passenger_business.svg';
            const currentRole = this.elements.characterRole ? this.elements.characterRole.textContent : 'Пассажир';
            const currentName = this.elements.characterName ? this.elements.characterName.textContent : 'Пассажир';
            const moodInfo = this.getMoodBadge(mood, text);
            const rawSpeech = this.getCleanSpeechText(text || '');
            const escapedText = rawSpeech.replace(/'/g, "\\'").replace(/"/g, '&quot;');
            const safeText = this.formatCleanDialogue(text || '');
            const evBadge = systemEvent ? `<div class="vsm-speech-subcontext"><i data-lucide="info" style="width: 15px; height: 15px; color: var(--vsm-cyan); flex-shrink: 0; margin-top: 2px;"></i><span>${systemEvent}</span></div>` : '';

            rowDiv.innerHTML = `
                <div class="vsm-passenger-frame-col">
                    <div class="vsm-passenger-avatar-box">
                        <img src="${currentAvatar}" alt="Пассажир ВСМ" class="vsm-passenger-avatar-img">
                    </div>
                    <div class="vsm-passenger-role-pill" title="Роль участника инцидента">
                        <span class="vsm-status-indicator-dot"></span>
                        <span>${currentRole}</span>
                    </div>
                </div>
                <div class="vsm-speech-bubble">
                    <div class="vsm-speech-header">
                        <div class="vsm-speech-speaker">
                            <span class="vsm-speaker-name">${currentName}</span>
                            <span class="vsm-mood-badge ${moodInfo.cls}">${moodInfo.label}</span>
                        </div>
                        <div class="vsm-speech-audio-controls">
                            <button class="vsm-tts-play-btn" onclick="window.vsmAudio ? window.vsmAudio.speakText('${escapedText}') : null" title="Озвучить реплику пассажира (TTS)" type="button">
                                <i data-lucide="volume-2" style="width: 14px; height: 14px;"></i>
                                <span>Озвучить</span>
                            </button>
                        </div>
                    </div>
                    <div class="vsm-speech-text">
                        ${safeText}
                    </div>
                    ${evBadge}
                </div>
            `;
        }

        feed.appendChild(rowDiv);
        feed.scrollTop = feed.scrollHeight;
        if (window.lucide) lucide.createIcons();
    }

    handleTimeout() {
        if (this.isProcessing) return;
        this.isProcessing = true;

        clearTimeout(this._processingWatchdog);
        this._processingWatchdog = setTimeout(() => {
            if (this.isProcessing) {
                console.warn('VSM Watchdog: сброс зависшего таймаута в симуляторе');
                this.isProcessing = false;
                document.querySelectorAll('.vsm-choice-btn').forEach(b => b.disabled = false);
            }
        }, 3500);

        if (window.vsmAudio) {
            window.vsmAudio.stopSpeech();
            window.vsmAudio.playEmergency();
        }
        this.showToast('ВРЕМЯ ИСТЕКЛО! Промедление на скорости 400 км/ч недопустимо!', 'danger');

        fetch(`/api/simulation/${this.sessionId}/choose/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken(),
            },
            body: JSON.stringify({ is_timeout: true }),
        })
        .then(res => {
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return res.json();
        })
        .then(data => {
            this.isProcessing = false;
            clearTimeout(this._processingWatchdog);
            try {
                if (data.is_fail && data.fail_info) {
                    this.showFailureModal(data.fail_info);
                } else if (data.is_terminal && data.redirect_url) {
                    setTimeout(() => {
                        window.location.href = data.redirect_url;
                    }, 1200);
                } else {
                    this.updateMetrics(data);
                    // Перезапуск таймера на текущем узле со штрафом
                    this.startTimer(15);
                }
            } catch (err) {
                console.error('Ошибка в handleTimeout response:', err);
                document.querySelectorAll('.vsm-choice-btn').forEach(b => b.disabled = false);
            }
        })
        .catch(err => {
            this.isProcessing = false;
            clearTimeout(this._processingWatchdog);
            console.error('Timeout error:', err);
            document.querySelectorAll('.vsm-choice-btn').forEach(b => b.disabled = false);
        });
    }

    choose(choiceId, choiceBtn) {
        if (this.isProcessing) return;
        this.isProcessing = true;
        clearInterval(this.timerInterval);

        clearTimeout(this._processingWatchdog);
        this._processingWatchdog = setTimeout(() => {
            if (this.isProcessing) {
                console.warn('VSM Watchdog: сброс зависшего выбора в симуляторе');
                this.isProcessing = false;
                document.querySelectorAll('.vsm-choice-btn').forEach(b => b.disabled = false);
            }
        }, 3500);

        if (choiceBtn) {
            choiceBtn.style.borderColor = '#00d2ff';
            choiceBtn.style.background = 'rgba(8, 42, 153, 0.6)';
        }

        if (window.vsmAudio) {
            window.vsmAudio.stopSpeech();
            window.vsmAudio.playClick();
        }

        fetch(`/api/simulation/${this.sessionId}/choose/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken(),
            },
            body: JSON.stringify({ choice_id: choiceId }),
        })
        .then(res => {
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return res.json();
        })
        .then(data => {
            this.isProcessing = false;
            clearTimeout(this._processingWatchdog);
            try {
                this.handleChoiceResponse(data);
            } catch (err) {
                console.error('Ошибка в handleChoiceResponse:', err);
                document.querySelectorAll('.vsm-choice-btn').forEach(b => b.disabled = false);
            }
        })
        .catch(err => {
            this.isProcessing = false;
            clearTimeout(this._processingWatchdog);
            console.error('Choice error:', err);
            document.querySelectorAll('.vsm-choice-btn').forEach(b => b.disabled = false);
            this.showToast('Ошибка передачи данных телеметрии', 'danger');
        });
    }

    handleChoiceResponse(data) {
        // Звуковой отклик
        if (window.vsmAudio) {
            if (data.audio === 'success') window.vsmAudio.playSuccess();
            else if (data.audio === 'emergency') window.vsmAudio.playEmergency();
            else if (data.audio === 'warning') window.vsmAudio.playWarning();
        }

        // Обновление шкал
        this.updateMetrics(data);

        // Показ уведомления
        if (data.toast) {
            this.showToast(data.toast, data.audio === 'emergency' ? 'danger' : 'success');
        }

        if (data.is_fail && data.fail_info) {
            this.showFailureModal(data.fail_info);
            return;
        }

        if (data.is_terminal && data.redirect_url) {
            setTimeout(() => {
                window.location.href = data.redirect_url;
            }, 1000);
            return;
        }

        // Рендер нового узла
        if (data.node) {
            this.renderNode(data.node, data.choices);
            this.startTimer(data.node.time_limit_seconds || 25);
        }
    }

    showSuccessModal(successInfo) {
        clearInterval(this.timerInterval);
        if (window.vsmAudio && window.vsmAudio.stopTrainAmbient) {
            window.vsmAudio.stopTrainAmbient();
        }
        const modal = document.getElementById('vsm-success-modal');
        if (!modal) {
            setTimeout(() => {
                window.location.href = successInfo.result_url || `/simulation/${this.sessionId}/result/`;
            }, 2000);
            return;
        }

        const titleEl = document.getElementById('vsm-success-title');
        const replyEl = document.getElementById('vsm-success-reply');
        const feedbackEl = document.getElementById('vsm-success-feedback');
        const scoreEl = document.getElementById('vsm-success-score');
        const xpEl = document.getElementById('vsm-success-xp');
        const resultBtn = document.getElementById('vsm-success-result-btn');

        if (titleEl) titleEl.textContent = successInfo.title || 'Смена успешно сдана!';
        if (replyEl) replyEl.textContent = successInfo.character_reply ? `«${successInfo.character_reply}»` : 'Пассажир поблагодарил поездную бригаду.';
        if (feedbackEl) feedbackEl.textContent = successInfo.feedback || 'Регламент действий в нештатных ситуациях ВСМ соблюден полностью.';
        if (scoreEl) scoreEl.textContent = `${successInfo.score || 95}/100`;
        if (xpEl) xpEl.textContent = `+${successInfo.earned_xp || 45} XP`;

        if (resultBtn) {
            resultBtn.onclick = () => {
                window.location.href = successInfo.result_url || `/simulation/${this.sessionId}/result/`;
            };
        }

        modal.style.display = 'flex';
        if (window.lucide) lucide.createIcons();
    }

    showFailureModal(failInfo) {
        clearInterval(this.timerInterval);
        if (window.vsmAudio && window.vsmAudio.stopTrainAmbient) {
            window.vsmAudio.stopTrainAmbient();
        }
        const modal = document.getElementById('vsm-fail-modal');
        if (!modal) {
            if (failInfo.result_url) window.location.href = failInfo.result_url;
            return;
        }

        const titleEl = document.getElementById('vsm-fail-title');
        const actionEl = document.getElementById('vsm-fail-action');
        const reportEl = document.getElementById('vsm-fail-report');
        const regEl = document.getElementById('vsm-fail-regulation');
        const solutionEl = document.getElementById('vsm-fail-solution');
        const restartBtn = document.getElementById('vsm-fail-restart-btn');
        const debriefBtn = document.getElementById('vsm-fail-debrief-btn');

        if (titleEl) titleEl.textContent = failInfo.title || failInfo.error_title || 'Сценарий провален';
        const actionText = failInfo.action_taken || failInfo.user_action;
        if (actionEl) actionEl.textContent = actionText ? `«${actionText}»` : 'Действие не выбрано / промедление';
        if (reportEl) reportEl.textContent = failInfo.resolution_report || failInfo.why_wrong || failInfo.mistake_analysis || failInfo.expert_comment || 'Нарушение регламента скоростного движения ВСМ.';
        if (regEl) regEl.textContent = failInfo.regulation_reference || 'ПТЭ железных дорог РФ и Стандарты обслуживания «Белый кречет»';
        if (solutionEl) solutionEl.textContent = failInfo.recommended_approach || failInfo.correct_solution || 'Соблюдайте пошаговый регламент действий в нештатных ситуациях.';

        if (restartBtn) {
            restartBtn.onclick = () => {
                window.location.href = failInfo.restart_url || window.location.pathname;
            };
        }

        if (debriefBtn) {
            debriefBtn.onclick = () => {
                window.location.href = failInfo.result_url || `/simulation/${this.sessionId}/result/`;
            };
        }

        modal.style.display = 'flex';
        if (window.lucide) lucide.createIcons();
    }

    renderNode(node, choices) {
        if (this.elements.characterName) this.elements.characterName.textContent = node.character_name;
        if (this.elements.characterRole) this.elements.characterRole.textContent = node.character_role;
        if (this.elements.dialogueText) this.elements.dialogueText.textContent = this.formatCleanDialogue(node.dialogue_text);
        if (this.elements.characterMood && node.character_mood) {
            this.elements.characterMood.textContent = node.character_mood;
        }
        if (this.elements.narrativeContext) {
            if (node.narrative_context) {
                if (this.elements.narrativeContextText) {
                    this.elements.narrativeContextText.textContent = node.narrative_context;
                } else {
                    this.elements.narrativeContext.textContent = node.narrative_context;
                }
                this.elements.narrativeContext.style.display = 'flex';
            } else {
                this.elements.narrativeContext.style.display = 'none';
            }
        }

        this.updatePassengerVisual(node.character_role, node.character_name, node.dialogue_text, node.character_mood);

        // Рендер кнопок вариантов
        if (this.elements.choicesContainer && choices) {
            this.elements.choicesContainer.innerHTML = '';
            choices.forEach((c, idx) => {
                const btn = document.createElement('button');
                btn.className = 'vsm-choice-btn';
                btn.onclick = () => this.choose(c.id, btn);
                btn.innerHTML = `
                    <div class="vsm-choice-num">${idx + 1}</div>
                    <div class="vsm-choice-content">
                        <div class="vsm-choice-title">${c.text}</div>
                        ${c.tactical_hint ? `<div class="vsm-choice-hint">${c.tactical_hint}</div>` : ''}
                    </div>
                `;
                this.elements.choicesContainer.appendChild(btn);
            });
        }

        // Звук шага + автоматическая озвучка реплики пассажира
        if (window.vsmAudio) {
            setTimeout(() => {
                window.vsmAudio.playTrainChime();
                if (window.vsmAudio.settings && window.vsmAudio.settings.ttsEnabled && node.dialogue_text) {
                    setTimeout(() => {
                        const spType = window.vsmAudio.detectSpeakerType ?
                            window.vsmAudio.detectSpeakerType(node.dialogue_text, node.character_name, node.character_role) : 'male';
                        window.vsmAudio.speak(node.dialogue_text, null, null, spType);
                    }, 650);
                }
            }, 250);
        }
    }

    toggleContextSpeech() {
        if (!window.vsmAudio) return;
        if (window.vsmAudio.isSpeaking) {
            window.vsmAudio.stopSpeech();
            return;
        }
        const text = this.elements.narrativeContextText?.textContent || 
                     document.getElementById('vsm-narrative-context-text')?.textContent;
        if (text && text.trim()) {
            window.vsmAudio.speak(text.trim(), null, null, 'system', true);
        }
    }

    updateMetrics(data) {
        if (data.current_loyalty !== undefined && this.elements.valLoyalty) {
            this.elements.valLoyalty.textContent = `${data.current_loyalty}%`;
            this.elements.fillLoyalty.style.width = `${data.current_loyalty}%`;
        }
        if (data.current_safety !== undefined && this.elements.valSafety) {
            this.elements.valSafety.textContent = `${data.current_safety}%`;
            this.elements.fillSafety.style.width = `${data.current_safety}%`;
        }
        if (data.current_service !== undefined && this.elements.valService) {
            this.elements.valService.textContent = `${data.current_service}%`;
            this.elements.fillService.style.width = `${data.current_service}%`;
        }
        if (data.current_stress !== undefined && this.elements.valStress) {
            this.elements.valStress.textContent = `${data.current_stress}%`;
            this.elements.fillStress.style.width = `${data.current_stress}%`;
        }
    }

    showToast(message, type = 'info') {
        if (!this.elements.toast) return;
        this.elements.toastMsg.textContent = message;
        this.elements.toast.className = `vsm-hud-toast show ${type}`;
        setTimeout(() => {
            this.elements.toast.classList.remove('show');
        }, 3200);
    }

    updateSpeed(newSpeed) {
        if (newSpeed === undefined || newSpeed === null) return;
        const spd = Math.max(0, parseInt(newSpeed || 0, 10));
        if (this.elements.speedo) {
            this.elements.speedo.dataset.baseSpeed = spd;
            this.elements.speedo.textContent = spd;
        }
        if (this.elements.speedoLed) {
            this.elements.speedoLed.dataset.baseSpeed = spd;
            this.elements.speedoLed.textContent = spd;
        }
    }

    startSpeedometerJitter() {
        if (!this.elements.speedo && !this.elements.speedoLed) return;
        setInterval(() => {
            const rawBase = this.elements.speedo?.dataset.baseSpeed ?? this.elements.speedoLed?.dataset.baseSpeed ?? '0';
            const baseSpeed = Math.max(0, parseInt(rawBase, 10));
            if (baseSpeed <= 0) {
                // На стоянке поезда скорость строго 0, никакого ухода в минус!
                if (this.elements.speedo) this.elements.speedo.textContent = 0;
                if (this.elements.speedoLed) this.elements.speedoLed.textContent = 0;
                return;
            }
            const jitter = Math.floor(Math.random() * 3) - 1; // -1, 0, +1
            const clamped = Math.max(0, baseSpeed + jitter);
            if (this.elements.speedo) this.elements.speedo.textContent = clamped;
            if (this.elements.speedoLed) this.elements.speedoLed.textContent = clamped;
        }, 1800);
    }

    updatePassengerVisual(role, name, dialogueText, mood) {
        const rLower = (role || '').toLowerCase();
        const nLower = (name || '').toLowerCase();
        const dLower = (dialogueText || '').toLowerCase();
        const fullText = `${rLower} ${nLower} ${dLower}`;
        let avatarSrc = '/static/simulator/img/passenger_business.svg';

        // 1. Бортовой компьютер, приборы, пульт электрооборудования, щит, СКНБ
        const isSystemDevice = rLower.includes('пульт') || nLower.includes('пульт') || 
                               rLower.includes('щит') || nLower.includes('щит') || 
                               rLower.includes('электрощит') || nLower.includes('электрощит') || 
                               rLower.includes('скнб') || nLower.includes('скнб') || 
                               rLower.includes('датчик') || nLower.includes('датчик') || 
                               rLower.includes('дефибриллятор') || nLower.includes('дефибриллятор') || 
                               /\bанд\b/i.test(`${rLower} ${nLower}`) || 
                               rLower.includes('бортовой компьютер') || nLower.includes('бортовой компьютер') || 
                               rLower.includes('автоматик') || nLower.includes('автоматик');

        // 2. Кабина машиниста, машинист поезда, диспетчер, электромеханик ПЭМ (только если не прибор!)
        const isMachinist = !isSystemDevice && (
                            rLower.includes('машинист') || nLower.includes('машинист') || 
                            rLower.includes('кабина') || nLower.includes('кабина') || 
                            rLower.includes('диспетчер') || nLower.includes('диспетчер') || 
                            rLower.includes('пэм') || nLower.includes('пэм') || 
                            rLower.includes('электромеханик') || nLower.includes('электромеханик'));

        if (isSystemDevice) {
            avatarSrc = '/static/simulator/img/system_monitor.svg';
        } else if (isMachinist) {
            avatarSrc = '/static/simulator/img/machinist.svg';
        }
        // 3. Маломобильные пассажиры (МГН / колясочники)
        else if (fullText.includes('маломобильн') || fullText.includes('инвалид') || 
                 fullText.includes('колясочн') || fullText.includes('кресло-коляск') || 
                 fullText.includes('кресле-коляск') || fullText.includes('мгн') || 
                 fullText.includes('подъемник')) {
            avatarSrc = '/static/simulator/img/passenger_mobility.svg';
        } 
        // 4. Пассажиры с острым медицинским состоянием (задыхается, отек Квинке, аллергия, сердце, инфаркт, обморок)
        else if (fullText.includes('задых') || fullText.includes('астм') || 
                 fullText.includes('аллерг') || fullText.includes('отек') || 
                 fullText.includes('квинке') || fullText.includes('удуш') || 
                 fullText.includes('хрип') || fullText.includes('не дышит') || 
                 fullText.includes('синеет') || fullText.includes('сердц') || 
                 fullText.includes('приступ') || fullText.includes('давлен') || 
                 fullText.includes('плохо') || fullText.includes('врач') || 
                 fullText.includes('медицин') || fullText.includes('больной') || 
                 fullText.includes('инфаркт') || fullText.includes('обморок')) {
            avatarSrc = '/static/simulator/img/passenger_sick.svg';
        } 
        // 5. Дебоширы, нетрезвые пассажиры, буяны
        else if (fullText.includes('пьян') || fullText.includes('нетрезв') || 
                 fullText.includes('алког') || fullText.includes('дебош') || 
                 fullText.includes('буян') || fullText.includes('молоток') || 
                 fullText.includes('дебошир') || fullText.includes('буйств') || 
                 fullText.includes('хулиган') || fullText.includes('опьянен') || 
                 fullText.includes('буянит') || fullText.includes('нарушитель')) {
            avatarSrc = '/static/simulator/img/passenger_brawler.svg';
        } 
        // 6. Прочие бортовые приборы и автоматика
        else if (fullText.includes('система') || fullText.includes('датчик') || 
                 fullText.includes('скнб') || fullText.includes('монитор') || 
                 fullText.includes('автоматик') || fullText.includes('пантограф') || 
                 /\bкз\b|коротк.*замыкан|к\.з\./.test(fullText) || 
                 fullText.includes('заземлен') || fullText.includes('дрон') || 
                 fullText.includes('бортовой') || fullText.includes('электрощит') ||
                 fullText.includes('утечк')) {
            avatarSrc = '/static/simulator/img/system_monitor.svg';
        } 
        // 7. Дети и родители
        else if (fullText.includes('ребенок') || fullText.includes('ребёнк') || 
                 fullText.includes('ребенк') || fullText.includes('дети') || 
                 fullText.includes('детьм') || fullText.includes('детск') || 
                 fullText.includes('малыш') || fullText.includes('младен') || 
                 fullText.includes('новорожд') || 
                 (fullText.includes('мама') && !fullText.includes('панама'))) {
            avatarSrc = '/static/simulator/img/passenger_parent.svg';
        } 
        // 8. Пожилые пассажиры
        else if (fullText.includes('пожил') || fullText.includes('пенсион') || 
                 fullText.includes('дедушк') || fullText.includes('бабушк') || 
                 fullText.includes('профессор') || fullText.includes('ветеран') || 
                 fullText.includes('старик')) {
            avatarSrc = '/static/simulator/img/passenger_elderly.svg';
        } 
        // 9. Молодые пассажиры
        else if (fullText.includes('молод') || fullText.includes('студент') || 
                 fullText.includes('парень') || fullText.includes('турист') || 
                 fullText.includes('наушник') || fullText.includes('блогер')) {
            avatarSrc = '/static/simulator/img/passenger_young.svg';
        } 
        // 10. Женщины
        else if (rLower.includes('женщин') || rLower.includes('дама') || 
                 rLower.includes('пассажирка') || rLower.includes('девушк') || 
                 nLower.includes('женщин') || nLower.includes('дама') || 
                 nLower.includes('пассажирка') || nLower.includes('девушк') || 
                 /\b(анна|елена|крылова)\b/i.test(`${rLower} ${nLower}`)) {
            avatarSrc = '/static/simulator/img/passenger_woman.svg';
        }

        let moodClass = 'vsm-mood-default';
        const moodLower = (mood || '').toLowerCase();
        if (avatarSrc.includes('machinist')) {
            moodClass = 'vsm-mood-default';
        } else if (avatarSrc.includes('system_monitor') || isSystemDevice) {
            moodClass = 'vsm-mood-system';
        } else if (moodLower.includes('агресс') || moodLower.includes('раздраж') || moodLower.includes('гнев') || 
                   moodLower.includes('критическ') || fullText.includes('сердц') || fullText.includes('инфаркт')) {
            moodClass = 'vsm-mood-danger';
        } else if (moodLower.includes('паник') || moodLower.includes('тревож') || moodLower.includes('беспокой') || moodLower.includes('испуг')) {
            moodClass = 'vsm-mood-warning';
        }

        if (this.elements.charAvatar) {
            this.elements.charAvatar.src = avatarSrc;
        }
        if (this.elements.characterMood) {
            this.elements.characterMood.className = `vsm-mood-badge ${moodClass}`;
        }
    }

    getCSRFToken() {
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
        return cookieValue || '';
    }
}

window.VSMSimulator = VSMSimulator;
