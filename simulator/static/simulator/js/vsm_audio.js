/**
 * Расширенный аудиодвижок и речевой синтез (TTS) тренажера ВСМ «Белый кречет».
 * Версия 3.0:
 * - Фоновый воркер предзагрузки реплик (Web Worker + IndexedDB + localStorage с квотой безопасности)
 * - Раздельные настройки дикторов: Мужской голос, Женский голос, Кибер-система / Робот для приборов
 * - ИИ-синтез по умолчанию везде, мгновенное воспроизведение из оффлайн-кэша (0 сек задержки)
 * - Звуковые эффекты ВСМ, амбиент 400 км/ч, тактильные клики и аварийная сигнализация
 */

// Компактный детерминированный MD5 для синхронизации хэшей с Python
function vsmMD5(str) {
    function rotateLeft(lValue, iShiftBits) {
        return (lValue << iShiftBits) | (lValue >>> (32 - iShiftBits));
    }
    function addUnsigned(lX, lY) {
        const lX4 = (lX & 0x40000000);
        const lY4 = (lY & 0x40000000);
        const lX8 = (lX & 0x80000000);
        const lY8 = (lY & 0x80000000);
        const lResult = (lX & 0x3FFFFFFF) + (lY & 0x3FFFFFFF);
        if (lX4 & lY4) return (lResult ^ 0x80000000 ^ lX8 ^ lY8);
        if (lX4 | lY4) {
            if (lResult & 0x40000000) return (lResult ^ 0xC0000000 ^ lX8 ^ lY8);
            else return (lResult ^ 0x40000000 ^ lX8 ^ lY8);
        } else {
            return (lResult ^ lX8 ^ lY8);
        }
    }
    function F(x, y, z) { return (x & y) | ((~x) & z); }
    function G(x, y, z) { return (x & z) | (y & (~z)); }
    function H(x, y, z) { return (x ^ y ^ z); }
    function I(x, y, z) { return (y ^ (x | (~z))); }
    function FF(a, b, c, d, x, s, ac) {
        a = addUnsigned(a, addUnsigned(addUnsigned(F(b, c, d), x), ac));
        return addUnsigned(rotateLeft(a, s), b);
    }
    function GG(a, b, c, d, x, s, ac) {
        a = addUnsigned(a, addUnsigned(addUnsigned(G(b, c, d), x), ac));
        return addUnsigned(rotateLeft(a, s), b);
    }
    function HH(a, b, c, d, x, s, ac) {
        a = addUnsigned(a, addUnsigned(addUnsigned(H(b, c, d), x), ac));
        return addUnsigned(rotateLeft(a, s), b);
    }
    function II(a, b, c, d, x, s, ac) {
        a = addUnsigned(a, addUnsigned(addUnsigned(I(b, c, d), x), ac));
        return addUnsigned(rotateLeft(a, s), b);
    }
    function convertToWordArray(string) {
        let lWordCount;
        const lMessageLength = string.length;
        const lNumberOfWords_temp1 = lMessageLength + 8;
        const lNumberOfWords_temp2 = (lNumberOfWords_temp1 - (lNumberOfWords_temp1 % 64)) / 64;
        const lNumberOfWords = (lNumberOfWords_temp2 + 1) * 16;
        const lWordArray = Array(lNumberOfWords - 1);
        let lBytePosition = 0;
        let lByteCount = 0;
        while (lByteCount < lMessageLength) {
            lWordCount = (lByteCount - (lByteCount % 4)) / 4;
            lBytePosition = (lByteCount % 4) * 8;
            lWordArray[lWordCount] = (lWordArray[lWordCount] | (string.charCodeAt(lByteCount) << lBytePosition));
            lByteCount++;
        }
        lWordCount = (lByteCount - (lByteCount % 4)) / 4;
        lBytePosition = (lByteCount % 4) * 8;
        lWordArray[lWordCount] = lWordArray[lWordCount] | (0x80 << lBytePosition);
        lWordArray[lNumberOfWords - 2] = lMessageLength << 3;
        lWordArray[lNumberOfWords - 1] = lMessageLength >>> 29;
        return lWordArray;
    }
    function wordToHex(lValue) {
        let WordToHexValue = '', WordToHexValue_temp = '', lByte, lCount;
        for (lCount = 0; lCount <= 3; lCount++) {
            lByte = (lValue >>> (lCount * 8)) & 255;
            WordToHexValue_temp = '0' + lByte.toString(16);
            WordToHexValue = WordToHexValue + WordToHexValue_temp.substr(WordToHexValue_temp.length - 2, 2);
        }
        return WordToHexValue;
    }

    const utf8Str = unescape(encodeURIComponent(str));
    const x = convertToWordArray(utf8Str);
    let a = 0x67452301, b = 0xEFCDAB89, c = 0x98BADCFE, d = 0x10325476;
    const S11 = 7, S12 = 12, S13 = 17, S14 = 22;
    const S21 = 5, S22 = 9, S23 = 14, S24 = 20;
    const S31 = 4, S32 = 11, S33 = 16, S34 = 23;
    const S41 = 6, S42 = 10, S43 = 15, S44 = 21;

    for (let k = 0; k < x.length; k += 16) {
        const AA = a, BB = b, CC = c, DD = d;
        a = FF(a, b, c, d, x[k + 0], S11, 0xD76AA478);
        d = FF(d, a, b, c, x[k + 1], S12, 0xE8C7B756);
        c = FF(c, d, a, b, x[k + 2], S13, 0x242070DB);
        b = FF(b, c, d, a, x[k + 3], S14, 0xC1BDCEEE);
        a = FF(a, b, c, d, x[k + 4], S11, 0xF57C0FAF);
        d = FF(d, a, b, c, x[k + 5], S12, 0x4787C62A);
        c = FF(c, d, a, b, x[k + 6], S13, 0xA8304613);
        b = FF(b, c, d, a, x[k + 7], S14, 0xFD469501);
        a = FF(a, b, c, d, x[k + 8], S11, 0x698098D8);
        d = FF(d, a, b, c, x[k + 9], S12, 0x8B44F7AF);
        c = FF(c, d, a, b, x[k + 10], S13, 0xFFFF5BB1);
        b = FF(b, c, d, a, x[k + 11], S14, 0x895CD7BE);
        a = FF(a, b, c, d, x[k + 12], S11, 0x6B901122);
        d = FF(d, a, b, c, x[k + 13], S12, 0xFD987193);
        c = FF(c, d, a, b, x[k + 14], S13, 0xA679438E);
        b = FF(b, c, d, a, x[k + 15], S14, 0x49B40821);

        a = GG(a, b, c, d, x[k + 1], S21, 0xF61E2562);
        d = GG(d, a, b, c, x[k + 6], S22, 0xC040B340);
        c = GG(c, d, a, b, x[k + 11], S23, 0x265E5A51);
        b = GG(b, c, d, a, x[k + 0], S24, 0xE9B6C7AA);
        a = GG(a, b, c, d, x[k + 5], S21, 0xD62F105D);
        d = GG(d, a, b, c, x[k + 10], S22, 0x2441453);
        c = GG(c, d, a, b, x[k + 15], S23, 0xD8A1E681);
        b = GG(b, c, d, a, x[k + 4], S24, 0xE7D3FBC8);
        a = GG(a, b, c, d, x[k + 9], S21, 0x21E1CDE6);
        d = GG(d, a, b, c, x[k + 14], S22, 0xC33707D6);
        c = GG(c, d, a, b, x[k + 3], S23, 0xF4D50D87);
        b = GG(b, c, d, a, x[k + 8], S24, 0x455A14ED);
        a = GG(a, b, c, d, x[k + 13], S21, 0xA9E3E905);
        d = GG(d, a, b, c, x[k + 2], S22, 0xFCEFA3F8);
        c = GG(c, d, a, b, x[k + 7], S23, 0x676F02D9);
        b = GG(b, c, d, a, x[k + 12], S24, 0x8D2A4C8A);

        a = HH(a, b, c, d, x[k + 5], S31, 0xFFFA3942);
        d = HH(d, a, b, c, x[k + 8], S32, 0x8771F681);
        c = HH(c, d, a, b, x[k + 11], S33, 0x6D9D6122);
        b = HH(b, c, d, a, x[k + 14], S34, 0xFDE5380C);
        a = HH(a, b, c, d, x[k + 1], S31, 0xA4BEEA44);
        d = HH(d, a, b, c, x[k + 4], S32, 0x4BDECFA9);
        c = HH(c, d, a, b, x[k + 7], S33, 0xF6BB4B60);
        b = HH(b, c, d, a, x[k + 10], S34, 0xBEBFBC70);
        a = HH(a, b, c, d, x[k + 13], S31, 0x289B7EC6);
        d = HH(d, a, b, c, x[k + 0], S32, 0xEAA127FA);
        c = HH(c, d, a, b, x[k + 3], S33, 0xD4EF3085);
        b = HH(b, c, d, a, x[k + 6], S34, 0x4881D05);
        a = HH(a, b, c, d, x[k + 9], S31, 0xD9D4D039);
        d = HH(d, a, b, c, x[k + 12], S32, 0xE6DB99E5);
        c = HH(c, d, a, b, x[k + 15], S33, 0x1FA27CF8);
        b = HH(b, c, d, a, x[k + 2], S34, 0xC4AC5665);

        a = II(a, b, c, d, x[k + 0], S41, 0xF4292244);
        d = II(d, a, b, c, x[k + 7], S42, 0x432AFF97);
        c = II(c, d, a, b, x[k + 14], S43, 0xAB9423A7);
        b = II(b, c, d, a, x[k + 5], S44, 0xFC93A039);
        a = II(a, b, c, d, x[k + 12], S41, 0x655B59C3);
        d = II(d, a, b, c, x[k + 3], S42, 0x8F0CCC92);
        c = II(c, d, a, b, x[k + 10], S43, 0xFFEFF47D);
        b = II(b, c, d, a, x[k + 1], S44, 0x85845DD1);
        a = II(a, b, c, d, x[k + 8], S41, 0x6FA87E4F);
        d = II(d, a, b, c, x[k + 15], S42, 0xFE2CE6E0);
        c = II(c, d, a, b, x[k + 6], S43, 0xA3014314);
        b = II(b, c, d, a, x[k + 13], S44, 0x4E0811A1);
        a = II(a, b, c, d, x[k + 4], S41, 0xF7537E82);
        d = II(d, a, b, c, x[k + 11], S42, 0xBD3AF235);
        c = II(c, d, a, b, x[k + 2], S43, 0x2AD7D2BB);
        b = II(b, c, d, a, x[k + 9], S44, 0xEB86D391);

        a = addUnsigned(a, AA);
        b = addUnsigned(b, BB);
        c = addUnsigned(c, CC);
        d = addUnsigned(d, DD);
    }
    return (wordToHex(a) + wordToHex(b) + wordToHex(c) + wordToHex(d)).toLowerCase();
}


/**
 * Менеджер клиентского хранилища аудио (IndexedDB + безопасная квота localStorage).
 * Оставляет гарантированный запас места в localStorage (>3.2 МБ), сохраняя все файлы в IndexedDB.
 */
class VSMAudioStorage {
    constructor() {
        this.db = null;
        this.dbPromise = this.initDB();
        this.memoryCache = new Map();
        this.MAX_RAM_ITEMS = 30; // Безопасный лимит оперативной памяти на кэш звуков
        this.cleanLegacyLocalStorage();
    }

    cleanLegacyLocalStorage() {
        // Очищаем старые тяжелые аудио-файлы из localStorage, чтобы освободить квоту браузера
        try {
            const keysToRemove = [];
            for (let i = 0; i < localStorage.length; i++) {
                const k = localStorage.key(i);
                if (k && k.startsWith('vsm_tts_c_')) keysToRemove.push(k);
            }
            keysToRemove.forEach(k => localStorage.removeItem(k));
        } catch (_) {}
    }

    async initDB() {
        if (!window.indexedDB) return null;
        return new Promise((resolve) => {
            try {
                const req = indexedDB.open('VSMAudioCacheDB', 1);
                req.onupgradeneeded = (e) => {
                    const db = e.target.result;
                    if (!db.objectStoreNames.contains('audios')) {
                        const store = db.createObjectStore('audios', { keyPath: 'key' });
                        store.createIndex('text', 'text', { unique: false });
                        store.createIndex('speakerType', 'speakerType', { unique: false });
                    }
                };
                req.onsuccess = () => {
                    this.db = req.result;
                    resolve(this.db);
                };
                req.onerror = () => resolve(null);
            } catch (_) {
                resolve(null);
            }
        });
    }

    async getAudio(key) {
        if (!key) return null;

        // 1. Быстрый RAM кэш (LRU)
        if (this.memoryCache.has(key)) {
            const val = this.memoryCache.get(key);
            this.memoryCache.delete(key);
            this.memoryCache.set(key, val);
            return val;
        }

        // 2. IndexedDB кэш (основная безлимитная база)
        try {
            await this.dbPromise;
            if (this.db) {
                const record = await new Promise((resolve) => {
                    const tx = this.db.transaction('audios', 'readonly');
                    const store = tx.objectStore('audios');
                    const req = store.get(key);
                    req.onsuccess = () => resolve(req.result);
                    req.onerror = () => resolve(null);
                });
                if (record && record.dataUrl) {
                    if (this.memoryCache.size >= this.MAX_RAM_ITEMS) {
                        const oldestKey = this.memoryCache.keys().next().value;
                        this.memoryCache.delete(oldestKey);
                    }
                    this.memoryCache.set(key, record.dataUrl);
                    return record.dataUrl;
                }
            }
        } catch (_) {}

        return null;
    }

    async saveAudio(key, dataUrl, meta = {}) {
        if (!key || !dataUrl) return;

        if (this.memoryCache.size >= this.MAX_RAM_ITEMS) {
            const oldestKey = this.memoryCache.keys().next().value;
            this.memoryCache.delete(oldestKey);
        }
        this.memoryCache.set(key, dataUrl);

        // Сохранение в IndexedDB (без лимитов памяти localStorage)
        try {
            await this.dbPromise;
            if (this.db) {
                const tx = this.db.transaction('audios', 'readwrite');
                const store = tx.objectStore('audios');
                store.put({
                    key,
                    dataUrl,
                    text: meta.text || '',
                    speakerType: meta.speakerType || 'male',
                    voice: meta.voice || '',
                    timestamp: Date.now()
                });
            }
        } catch (_) {}
    }

    async clearCache() {
        this.memoryCache.clear();
        this.cleanLegacyLocalStorage();
        try {
            await this.dbPromise;
            if (this.db) {
                const tx = this.db.transaction('audios', 'readwrite');
                tx.objectStore('audios').clear();
            }
        } catch (_) {}
    }

    async getStats() {
        let inIndexedDB = 0;
        try {
            await this.dbPromise;
            if (this.db) {
                inIndexedDB = await new Promise((resolve) => {
                    const tx = this.db.transaction('audios', 'readonly');
                    const req = tx.objectStore('audios').count();
                    req.onsuccess = () => resolve(req.result || 0);
                    req.onerror = () => resolve(0);
                });
            }
        } catch (_) {}

        return {
            totalIndexedDB: inIndexedDB,
            inLocalStorage: 0,
            inMemory: this.memoryCache.size
        };
    }
}


/**
 * Менеджер фонового Web Worker для загрузки всех озвучек в фоне
 */
class VSMTTSPreloader {
    constructor(audioEngine) {
        this.audio = audioEngine;
        this.worker = null;
        this.items = [];
        this.total = 0;
        this.loaded = 0;
        this.isWorking = false;
        this.textToHash = new Map();
    }

    async init() {
        try {
            const res = await fetch('/api/v1/tts/preload-list/');
            if (!res.ok) return;
            const data = await res.json();
            if (data && data.success && Array.isArray(data.items)) {
                this.items = data.items;
                this.total = this.items.length;
                this.items.forEach(it => {
                    if (it.text && it.hash) {
                        this.textToHash.set(it.text.trim(), it.hash);
                    }
                });
                this.startWorker();
            }
        } catch (_) {}
    }

    startWorker() {
        if (this.isWorking || !this.items || this.items.length === 0) return;
        this.isWorking = true;

        if (window.Worker) {
            try {
                this.worker = new Worker('/static/simulator/js/vsm_tts_worker.js');
                this.worker.onmessage = (e) => this.handleWorkerMessage(e.data);
                this.worker.postMessage({
                    action: 'START_PRELOAD',
                    items: this.items
                });
                return;
            } catch (_) {
                // Если запуск Worker заблокирован политикой браузера, запускаем встроенный цикл
            }
        }

        this.fallbackPreload();
    }

    handleWorkerMessage(data) {
        if (!data) return;
        if (data.type === 'ITEM_EXISTS' || data.type === 'ITEM_LOADED') {
            this.loaded = data.completed || (this.loaded + 1);
            if (!this._lastUiUpdate || Date.now() - this._lastUiUpdate > 300) {
                this._lastUiUpdate = Date.now();
                this.updateUI();
            }
        } else if (data.type === 'PRELOAD_COMPLETE') {
            this.isWorking = false;
            this.updateUI();
        }
    }

    async fallbackPreload() {
        for (let i = 0; i < this.items.length; i++) {
            const it = this.items[i];
            const cached = await this.audio.storage.getAudio(it.hash);
            if (cached) {
                this.loaded++;
                if (!this._lastUiUpdate || Date.now() - this._lastUiUpdate > 300) {
                    this._lastUiUpdate = Date.now();
                    this.updateUI();
                }
                continue;
            }

            try {
                const params = new URLSearchParams({
                    text: it.text,
                    voice: it.voice || 'ru-RU-DmitryNeural',
                    rate: it.rate || '+0%',
                    pitch: it.pitch || '+0Hz',
                });
                const res = await fetch(`/api/v1/tts/?${params.toString()}`);
                if (res.ok) {
                    const json = await res.json();
                    if (json && json.audio_url) {
                        const fileRes = await fetch(json.audio_url);
                        if (fileRes.ok) {
                            const blob = await fileRes.blob();
                            const reader = new FileReader();
                            reader.onloadend = () => {
                                this.audio.storage.saveAudio(it.hash, reader.result, {
                                    text: it.text,
                                    speakerType: it.speaker_type
                                });
                            };
                            reader.readAsDataURL(blob);
                        }
                    }
                }
            } catch (_) {}

            this.loaded++;
            if (!this._lastUiUpdate || Date.now() - this._lastUiUpdate > 300) {
                this._lastUiUpdate = Date.now();
                this.updateUI();
            }
            await new Promise(r => setTimeout(r, 150));
        }
        this.isWorking = false;
        this.updateUI();
    }

    async updateUI() {
        const stats = await this.audio.storage.getStats();
        const count = Math.max(this.loaded, stats.totalIndexedDB);
        const total = Math.max(this.total, 125);
        const pct = Math.min(100, Math.round((count / total) * 100));

        const bar = document.getElementById('vsm-tts-cache-bar');
        const pctEl = document.getElementById('vsm-tts-cache-pct');
        const textEl = document.getElementById('vsm-tts-cache-status-text');

        if (bar) bar.style.width = `${pct}%`;
        if (pctEl) pctEl.textContent = `${pct}%`;
        if (textEl) {
            if (pct >= 95) {
                textEl.textContent = `Кэшировано: ${count} из ${total} фраз (100% готовность к офлайн-игре в IndexedDB).`;
            } else {
                textEl.textContent = `Фоновая предзагрузка реплик в кэш IndexedDB: ${count} / ${total} (${pct}%).`;
            }
        }
    }
}


/**
 * Главный аудиодвижок тренажера ВСМ
 */
class VSMAudioEngine {
    constructor() {
        this.ctx = null;
        this.synth = window.speechSynthesis || null;
        this.currentUtterance = null;
        this.currentTTSAudio = null;
        this.isSpeaking = false;
        this.ambientAudio = null;
        this.speakSessionId = 0;
        this.currentFetchController = null;

        this.storage = new VSMAudioStorage();
        this.preloader = new VSMTTSPreloader(this);

        // Список нейросетевых голосов ВСМ (Azure Neural AI)
        this.neuralVoices = [
            { id: 'ru-RU-DmitryNeural', name: 'Дмитрий (Нейросеть ВСМ, Мужской)', lang: 'ru-RU' },
            { id: 'ru-RU-SvetlanaNeural', name: 'Светлана (Нейросеть ВСМ, Женский)', lang: 'ru-RU' },
            { id: 'robot-telemetry', name: 'Бортовой компьютер ВСМ (Роботизированный женский)', lang: 'ru-RU' },
            { id: 'machinist-radio', name: 'Кабина машиниста (Рация интеркома)', lang: 'ru-RU' },
            { id: 'en-US-JennyNeural', name: 'Jenny (Neural EN, Female)', lang: 'en-US' },
            { id: 'en-US-GuyNeural', name: 'Guy (Neural EN, Male)', lang: 'en-US' },
        ];

        // Загрузка настроек с раздельными голосами
        this.settings = {
            muted: localStorage.getItem('vsm_audio_muted') === 'true',
            masterVolume: parseFloat(localStorage.getItem('vsm_audio_master_vol') ?? '0.8'),
            sfxVolume: parseFloat(localStorage.getItem('vsm_audio_sfx_vol') ?? '0.85'),
            chimeEnabled: localStorage.getItem('vsm_audio_chime_enabled') !== 'false',
            clickEnabled: localStorage.getItem('vsm_audio_click_enabled') !== 'false',
            warningEnabled: localStorage.getItem('vsm_audio_warning_enabled') !== 'false',
            ambientEnabled: localStorage.getItem('vsm_audio_ambient_enabled') !== 'false',
            ambientVolume: parseFloat(localStorage.getItem('vsm_audio_ambient_vol') ?? '0.10'),
            ttsEnabled: localStorage.getItem('vsm_audio_tts_enabled') !== 'false',
            ttsVolume: parseFloat(localStorage.getItem('vsm_audio_tts_vol') ?? '0.9'),
            ttsRate: parseFloat(localStorage.getItem('vsm_audio_tts_rate') ?? '1.0'),
            ttsPitch: parseFloat(localStorage.getItem('vsm_audio_tts_pitch') ?? '1.0'),
            ttsVoiceMale: localStorage.getItem('vsm_audio_tts_voice_male') || 'ru-RU-DmitryNeural',
            ttsVoiceFemale: localStorage.getItem('vsm_audio_tts_voice_female') || 'ru-RU-SvetlanaNeural',
            ttsVoiceSystem: localStorage.getItem('vsm_audio_tts_voice_system') || 'robot-telemetry',
            ttsVoiceMachinist: localStorage.getItem('vsm_audio_tts_voice_machinist') || 'machinist-radio',
            ttsVoice: localStorage.getItem('vsm_audio_tts_voice') || 'ru-RU-DmitryNeural',
        };

        // Кэш сэмплов поезда
        this.soundUrls = {
            chime: '/static/simulator/audio/chime_melodic.mp3',
            click: '/static/simulator/audio/click_soft.mp3',
            success: '/static/simulator/audio/success_complete.mp3',
            warning: '/static/simulator/audio/warning_tone.mp3',
            emergency: '/static/simulator/audio/emergency_alarm.mp3',
            ambient: '/static/simulator/audio/train_ambient.mp3',
            door: '/static/simulator/audio/door_chime.mp3',
            achievement: '/static/simulator/audio/achievement.mp3',
        };

        this.voices = [];
        this.initTTSVoices();
        this.preloadAudio();

        // Автозапуск фонового эмбиента везде при загрузке или первом же взаимодействии пользователя
        this.unlocked = false;
        this.pendingPlayCallbacks = [];
        this.setupAutoAmbientAndUnlock();

        // Запуск фоновой предзагрузки через 1.2 сек после готовности страницы
        setTimeout(() => {
            this.preloader.init();
        }, 1200);
    }

    get isMuted() {
        return this.settings.muted;
    }

    set isMuted(val) {
        this.settings.muted = Boolean(val);
        localStorage.setItem('vsm_audio_muted', this.settings.muted);
    }

    initContext() {
        if (!this.ctx) {
            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            if (AudioCtx) this.ctx = new AudioCtx();
        }
        if (this.ctx && this.ctx.state === 'suspended') {
            this.ctx.resume().catch(() => {});
        }
    }

    preloadAudio() {
        Object.entries(this.soundUrls).forEach(([key, url]) => {
            if (key === 'ambient') return;
            try {
                const a = new Audio(url);
                a.preload = 'auto';
            } catch (_) {}
        });
    }

    setupAutoAmbientAndUnlock() {
        const unlockAndStart = () => {
            this.unlocked = true;
            this.initContext();

            if (this.settings.ambientEnabled && !this.isMuted) {
                this.startAmbient();
            }

            while (this.pendingPlayCallbacks.length > 0) {
                const cb = this.pendingPlayCallbacks.shift();
                try { cb(); } catch (_) {}
            }

            if (this.ambientAudio && !this.ambientAudio.paused) {
                interactionEvents.forEach(evt => {
                    window.removeEventListener(evt, unlockAndStart, true);
                });
            }
        };

        const interactionEvents = ['click', 'touchend', 'keydown', 'pointerdown'];

        // 1. Попытка немедленного запуска (работает при активном MEI или внутренних переходах)
        if (this.settings.ambientEnabled && !this.isMuted) {
            this.startAmbient();
        }

        // 2. Слушатели на window в фазе захвата (capture: true) для любого клика/касания
        interactionEvents.forEach(evt => {
            window.addEventListener(evt, unlockAndStart, { capture: true, passive: true });
        });

        // 3. Автоматическая пауза при переходе на другую вкладку браузера и возобновление при возврате
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                if (this.ambientAudio && !this.ambientAudio.paused) {
                    this._wasAmbientPlayingBeforeHide = true;
                    this.ambientAudio.pause();
                }
            } else {
                if (this._wasAmbientPlayingBeforeHide && this.settings.ambientEnabled && !this.isMuted) {
                    this._wasAmbientPlayingBeforeHide = false;
                    this.startAmbient();
                }
            }
        });
    }

    initTTSVoices() {
        if (!this.synth) return;
        const load = () => {
            const allVoices = this.synth.getVoices() || [];
            if (allVoices.length > 0) {
                this.voices = allVoices.sort((a, b) => {
                    const aRu = (a.lang || '').toLowerCase().startsWith('ru');
                    const bRu = (b.lang || '').toLowerCase().startsWith('ru');
                    if (aRu && !bRu) return -1;
                    if (!aRu && bRu) return 1;
                    return (a.name || '').localeCompare(b.name || '');
                });
                this.syncModalInputs();
            }
        };
        load();
        if (this.synth.onvoiceschanged !== undefined) {
            this.synth.onvoiceschanged = load;
        }
    }

    saveSettings() {
        localStorage.setItem('vsm_audio_muted', this.settings.muted);
        localStorage.setItem('vsm_audio_master_vol', this.settings.masterVolume);
        localStorage.setItem('vsm_audio_sfx_vol', this.settings.sfxVolume);
        localStorage.setItem('vsm_audio_chime_enabled', this.settings.chimeEnabled);
        localStorage.setItem('vsm_audio_click_enabled', this.settings.clickEnabled);
        localStorage.setItem('vsm_audio_warning_enabled', this.settings.warningEnabled);
        localStorage.setItem('vsm_audio_ambient_enabled', this.settings.ambientEnabled);
        localStorage.setItem('vsm_audio_ambient_vol', this.settings.ambientVolume);
        localStorage.setItem('vsm_audio_tts_enabled', this.settings.ttsEnabled);
        localStorage.setItem('vsm_audio_tts_vol', this.settings.ttsVolume);
        localStorage.setItem('vsm_audio_tts_rate', this.settings.ttsRate);
        localStorage.setItem('vsm_audio_tts_pitch', this.settings.ttsPitch);
        localStorage.setItem('vsm_audio_tts_voice_male', this.settings.ttsVoiceMale);
        localStorage.setItem('vsm_audio_tts_voice_female', this.settings.ttsVoiceFemale);
        localStorage.setItem('vsm_audio_tts_voice_system', this.settings.ttsVoiceSystem);
        localStorage.setItem('vsm_audio_tts_voice_machinist', this.settings.ttsVoiceMachinist);
    }

    updateVoiceSelection(type, val) {
        if (type === 'male') this.settings.ttsVoiceMale = val;
        else if (type === 'female') this.settings.ttsVoiceFemale = val;
        else if (type === 'system') this.settings.ttsVoiceSystem = val;
        else if (type === 'machinist') this.settings.ttsVoiceMachinist = val;
        this.saveSettings();
    }

    // Воспроизведение звуковых эффектов
    playSound(key, volumeScale = 1.0) {
        if (this.isMuted) return;
        const effectiveVol = Math.max(0, Math.min(1, this.settings.masterVolume * this.settings.sfxVolume * volumeScale));
        if (effectiveVol <= 0.001) return;

        const url = this.soundUrls[key];
        if (url) {
            try {
                const audio = new Audio(url);
                audio.volume = effectiveVol;
                audio.play().catch(() => this.playSynthesizedFallback(key));
            } catch (_) {
                this.playSynthesizedFallback(key);
            }
        } else {
            this.playSynthesizedFallback(key);
        }
    }

    playSynthesizedFallback(key) {
        try {
            this.initContext();
            if (!this.ctx) return;
            const now = this.ctx.currentTime;
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.connect(gain);
            gain.connect(this.ctx.destination);
            const vol = this.settings.masterVolume * this.settings.sfxVolume;

            if (key === 'click') {
                osc.type = 'sine';
                osc.frequency.setValueAtTime(600, now);
                osc.frequency.exponentialRampToValueAtTime(150, now + 0.035);
                gain.gain.setValueAtTime(vol * 0.15, now);
                gain.gain.exponentialRampToValueAtTime(0.001, now + 0.035);
                osc.start(now);
                osc.stop(now + 0.035);
            } else if (key === 'chime') {
                osc.type = 'sine';
                osc.frequency.setValueAtTime(523.25, now);
                osc.frequency.setValueAtTime(659.25, now + 0.15);
                gain.gain.setValueAtTime(vol * 0.25, now);
                gain.gain.exponentialRampToValueAtTime(0.001, now + 0.5);
                osc.start(now);
                osc.stop(now + 0.5);
            } else if (key === 'warning') {
                osc.type = 'triangle';
                osc.frequency.setValueAtTime(440, now);
                osc.frequency.setValueAtTime(554.37, now + 0.08);
                gain.gain.setValueAtTime(vol * 0.3, now);
                gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
                osc.start(now);
                osc.stop(now + 0.35);
            }
        } catch (_) {}
    }

    playClick() { if (this.settings.clickEnabled) this.playSound('click', 0.8); }
    playTrainChime() { if (this.settings.chimeEnabled) this.playSound('chime', 0.9); }
    playSuccess() { this.playSound('success', 0.9); }
    playWarning() { if (this.settings.warningEnabled) this.playSound('warning', 0.85); }
    playEmergency() { this.playSound('emergency', 1.0); }
    playDoorChime() { this.playSound('door', 0.85); }

    // Футуристический кибер-сигнал перед речью бортового компьютера и приборов ВСМ
    playSystemTelemetryBeep() {
        if (this.isMuted) return;
        try {
            this.initContext();
            if (!this.ctx) return;
            const now = this.ctx.currentTime;
            
            // Двойной металлический гармонический перезвон (1180Гц + 2360Гц)
            const osc1 = this.ctx.createOscillator();
            const osc2 = this.ctx.createOscillator();
            const gain = this.ctx.createGain();

            osc1.type = 'sine';
            osc1.frequency.setValueAtTime(1180, now);
            osc1.frequency.exponentialRampToValueAtTime(1760, now + 0.05);

            osc2.type = 'triangle';
            osc2.frequency.setValueAtTime(2360, now + 0.04);
            osc2.frequency.exponentialRampToValueAtTime(1580, now + 0.11);

            const vol = this.settings.masterVolume * this.settings.sfxVolume * 0.12;
            gain.gain.setValueAtTime(vol, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.14);

            osc1.connect(gain);
            osc2.connect(gain);
            gain.connect(this.ctx.destination);

            osc1.start(now);
            osc1.stop(now + 0.05);
            osc2.start(now + 0.04);
            osc2.stop(now + 0.14);
        } catch (_) {}
    }

    // Характерный щелчок/писк интеркома рации перед выходом в эфир кабины машиниста
    playMachinistRadioChirp() {
        if (this.isMuted) return;
        try {
            this.initContext();
            if (!this.ctx) return;
            const now = this.ctx.currentTime;
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();

            osc.type = 'sawtooth';
            osc.frequency.setValueAtTime(980, now);
            osc.frequency.setValueAtTime(490, now + 0.04);

            const vol = this.settings.masterVolume * this.settings.sfxVolume * 0.08;
            gain.gain.setValueAtTime(vol, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.06);

            osc.connect(gain);
            gain.connect(this.ctx.destination);

            osc.start(now);
            osc.stop(now + 0.06);
        } catch (_) {}
    }

    // Фоновый эмбиент движения поезда ВСМ (действует по всей платформе ВСМ)
    startTrainAmbient() {
        this.startAmbient();
    }

    stopTrainAmbient() {
        // Фоновый эмбиент действует непрерывно по всей платформе ВСМ
    }

    startAmbient() {
        if (this.isMuted || !this.settings.ambientEnabled) return;
        if (!this.ambientAudio) {
            this.ambientAudio = new Audio(this.soundUrls.ambient);
            this.ambientAudio.loop = true;
            this.ambientAudio.preload = 'auto';
        }
        const vol = Math.max(0, Math.min(1, this.settings.masterVolume * this.settings.ambientVolume));
        this.ambientAudio.volume = vol;
        if (this.ambientAudio.paused) {
            const playPromise = this.ambientAudio.play();
            if (playPromise !== undefined) {
                playPromise.catch(() => {
                    // Браузер ожидает взаимодействия (будет запущен по capture-слушателю)
                });
            }
        }
    }

    stopAmbient() {
        this._wasAmbientPlayingBeforeHide = false;
        if (this.ambientAudio) {
            this.ambientAudio.pause();
            this.ambientAudio.currentTime = 0;
        }
    }

    updateAmbientVolume() {
        if (!this.ambientAudio) return;
        if (this.isMuted || !this.settings.ambientEnabled) {
            this.ambientAudio.pause();
        } else {
            const vol = Math.max(0, Math.min(1, this.settings.masterVolume * this.settings.ambientVolume));
            this.ambientAudio.volume = vol;
            if (this.ambientAudio.paused) this.ambientAudio.play().catch(() => {});
        }
    }

    // --- Определение типа диктора (бортовой журнал-робот / машинист-рация / женщина / мужчина) ---
    detectSpeakerType(text = '', characterName = '', characterRole = '') {
        const domName = characterName || document.getElementById('card-character-name')?.textContent || 
                        document.getElementById('vsm-character-name')?.textContent || '';
        const domRole = characterRole || document.getElementById('card-character-role')?.textContent || 
                        document.getElementById('vsm-character-role')?.textContent || '';

        const nLower = `${characterName || ''} ${domName}`.toLowerCase();
        const rLower = `${characterRole || ''} ${domRole}`.toLowerCase();
        const txtLower = (text || '').toLowerCase();

        // 1. Бортовой журнал, приборы, пульт, электрощит, СКНБ, дефибриллятор АНД, датчики, телеметрия (роботизированный электронный)
        const systemDirect = [
            'журнал', 'бортжурнал', 'бортовой журнал', 'пульт', 'электрощит', 'электрооборудован',
            'скнб', 'дефибриллятор', 'дефибр', 'датчик', 'телеметри', 'автоматик',
            'бортовой компьютер', 'эвм', 'монитор', 'автоинформатор', 'система',
            'оповещение системы', 'сигнализация', 'лог', 'бортовая система'
        ];
        const isDeviceExact = /\bанд\b|\bщит\b/i.test(`${rLower} ${nLower}`);
        if (systemDirect.some(k => rLower.includes(k) || nLower.includes(k)) || isDeviceExact) {
            return 'system';
        }

        // 2. Кабина машиниста, машинист состава, поездной диспетчер, ПЭМ, электромеханик (рация интеркома, мужской)
        const machinistDirect = ['машинист', 'кабина', 'кабины', 'диспетчер', 'днц', 'пэм', 'электромеханик', 'рация', 'интерком'];
        if (machinistDirect.some(k => rLower.includes(k) || nLower.includes(k))) {
            return 'machinist';
        }

        // 3. Женщины (строго по роли, имени или грамматике первого лица женского рода) - ДО мужчин!
        const femaleRoles = [
            'пассажирка', 'женщин', 'девушк', 'мама', 'мать', 'бабушк', 'женск',
            'крылова', 'стюардесса', 'проводница', 'соколова', 'иванова', 'смирнова',
            'кузнецова', 'попова', 'васильева'
        ];
        if (femaleRoles.some(k => rLower.includes(k) || nLower.includes(k))) {
            return 'female';
        }

        if (/\b(анна|елена|ольга|светлана|екатерина|мария|ирина|наталья|татьяна|дарья|алёна|алена|виктория|оксана|юлия|надежда|полина|ксения|валентина|людмила|любовь|марина|алина|вероника|софия|евгения|лариса|галина|нина|инна|вера)\b/i.test(`${rLower} ${nLower}`)) {
            return 'female';
        }

        if (/\b(я согласна|я сама|я готова|я заплатила|я села|я забыла|я опоздала|я испугалась|я увидела|я заметила|я подошла|я попросила|я спросила|я решила|я купила|я ехала)\b/i.test(txtLower)) {
            return 'female';
        }

        // 4. Мужчины (пассажиры, дебоширы, ревизоры, дедушки, студенты и по умолчанию)
        return 'male';
    }

    resolveVoice(speakerType) {
        if (speakerType === 'female') return this.settings.ttsVoiceFemale || 'ru-RU-SvetlanaNeural';
        if (speakerType === 'system') return this.settings.ttsVoiceSystem || 'robot-telemetry';
        if (speakerType === 'machinist') return this.settings.ttsVoiceMachinist || 'machinist-radio';
        return this.settings.ttsVoiceMale || 'ru-RU-DmitryNeural';
    }

    // Очистка текста от мусора (озвучивается ТОЛЬКО прямая речь, без ремарок в скобках)
    cleanSpeechText(raw) {
        if (!raw) return '';
        // 1. Удаляем сценические ремарки в скобках: (плачет), [кашляет], (кричит), {тихо} и т.д.
        let textToSpeak = raw.replace(/\([^)]*\)/g, ' ').replace(/\[[^\]]*\]/g, ' ').replace(/\{[^}]*\}/g, ' ');

        const quoteMatches = textToSpeak.match(/«([^»]+)»/g) || textToSpeak.match(/"([^"]+)"/g);
        if (quoteMatches && quoteMatches.length > 0) {
            textToSpeak = quoteMatches.map(m => m.replace(/^[«"]|[»"]$/g, '').trim()).join(' ');
        } else {
            const colonIdx = textToSpeak.indexOf(':');
            if (colonIdx !== -1 && colonIdx < 45) {
                textToSpeak = textToSpeak.slice(colonIdx + 1).trim();
            }
        }

        // 2. Повторная зачистка на случай скобок внутри цитаты
        textToSpeak = textToSpeak.replace(/\([^)]*\)/g, ' ').replace(/\[[^\]]*\]/g, ' ').replace(/\{[^}]*\}/g, ' ');

        return textToSpeak
            .replace(/[«»"“”„_#*`]/g, '')
            .replace(/[—–]/g, ' - ')
            .replace(/\s+/g, ' ')
            .replace(/п\.\s*(\d+)/g, 'пункт $1')
            .replace(/ВСМ/g, 'В С М')
            .trim();
    }

    // --- Главная точка входа воспроизведения речи ---
    async speak(text, onStart = null, onEnd = null, explicitSpeakerType = null, forcePlay = false) {
        this.stopSpeech();
        if (this.isMuted || (!this.settings.ttsEnabled && !forcePlay)) {
            if (onEnd) onEnd();
            return;
        }

        const clean = this.cleanSpeechText(text);
        if (!clean) {
            if (onEnd) onEnd();
            return;
        }

        const currentSessionId = this.speakSessionId;

        const speakerType = explicitSpeakerType || this.detectSpeakerType(clean);
        const voiceKey = this.resolveVoice(speakerType);
        const isSystem = (speakerType === 'system');
        const isMachinist = (speakerType === 'machinist');

        let actualVoice = voiceKey;
        let rateStr = '+0%';
        let pitchStr = '+0Hz';

        if (voiceKey === 'robot-telemetry' || isSystem) {
            actualVoice = 'ru-RU-SvetlanaNeural';
            rateStr = '+18%';
            pitchStr = '+30Hz';
        } else if (voiceKey === 'machinist-radio' || isMachinist) {
            actualVoice = 'ru-RU-DmitryNeural';
            rateStr = '+10%';
            pitchStr = '-20Hz';
        }

        const isLocalVoice = voiceKey.startsWith('local');
        const signature = `${actualVoice}_${rateStr}_${pitchStr}_${clean}`;
        const hash = this.preloader.textToHash.get(clean) || vsmMD5(signature);

        // 1. Проверяем наличие в клиентском кэше (IndexedDB)
        const cachedDataUrl = await this.storage.getAudio(hash);
        if (this.speakSessionId !== currentSessionId) return;

        if (cachedDataUrl) {
            if (isSystem) this.playSystemTelemetryBeep();
            else if (isMachinist) this.playMachinistRadioChirp();
            this.playAudioFromUrl(cachedDataUrl, clean, speakerType, onStart, onEnd, currentSessionId);
            return;
        }

        // 2. Если выбран локальный голос устройства (Web Speech API)
        if (isLocalVoice) {
            this.speakLocalUtterance(clean, speakerType, onStart, onEnd, currentSessionId);
            return;
        }

        // 3. Запрос к нейросетевому синтезу с быстрым таймаутом на случай сетевых задержек
        this.updateTTSButtonState(false, true);

        const params = new URLSearchParams({
            text: clean,
            voice: voiceKey,
            rate: rateStr,
            pitch: pitchStr,
        });

        const controller = new AbortController();
        this.currentFetchController = controller;
        const fetchTimeout = setTimeout(() => controller.abort(), 12000);

        try {
            const res = await fetch(`/api/v1/tts/?${params.toString()}`, { signal: controller.signal });
            clearTimeout(fetchTimeout);
            this.currentFetchController = null;
            if (this.speakSessionId !== currentSessionId) return;

            if (res.ok) {
                const data = await res.json();
                if (this.speakSessionId !== currentSessionId) return;

                if (data && data.success && data.audio_url) {
                    if (isSystem) this.playSystemTelemetryBeep();
                    else if (isMachinist) this.playMachinistRadioChirp();

                    // Воспроизведение
                    this.playAudioFromUrl(data.audio_url, clean, speakerType, onStart, onEnd, currentSessionId);

                    // Сохранение в оффлайн-кэш для мгновенных повторов
                    fetch(data.audio_url)
                        .then(f => f.blob())
                        .then(blob => {
                            const reader = new FileReader();
                            reader.onloadend = () => {
                                this.storage.saveAudio(hash, reader.result, {
                                    text: clean,
                                    speakerType: speakerType,
                                    voice: voiceKey
                                });
                            };
                            reader.readAsDataURL(blob);
                        }).catch(() => {});
                    return;
                }
            }
        } catch (_) {
            clearTimeout(fetchTimeout);
            this.currentFetchController = null;
        }

        if (this.speakSessionId !== currentSessionId) return;

        // Попытка прямого потокового воспроизведения через бортовой комплекс TTS
        try {
            const liveStreamUrl = `/api/v1/live/tts/?text=${encodeURIComponent(clean)}&voice=${encodeURIComponent(actualVoice)}&format=opus`;
            if (isSystem) this.playSystemTelemetryBeep();
            else if (isMachinist) this.playMachinistRadioChirp();
            this.playAudioFromUrl(liveStreamUrl, clean, speakerType, onStart, onEnd, currentSessionId);
            return;
        } catch (_) {}

        if (this.speakSessionId !== currentSessionId) return;

        // Резервный переход на локальный голос при сбое сети
        this.speakLocalUtterance(clean, speakerType, onStart, onEnd, currentSessionId);
    }

    playAudioFromUrl(url, textToFallback = '', speakerType = 'male', onStart = null, onEnd = null, expectedSessionId = null) {
        if (expectedSessionId && this.speakSessionId !== expectedSessionId) return;

        try {
            const audio = new Audio(url);
            this.currentTTSAudio = audio;
            const effectiveVol = Math.max(0, Math.min(1, this.settings.masterVolume * this.settings.ttsVolume));
            audio.volume = effectiveVol;

            // Аппаратный DSP-эффект бортового компьютера вагона ВСМ (роботизированный полосовой фильтр)
            if (speakerType === 'system') {
                this.initContext();
                if (this.ctx) {
                    try {
                        const source = this.ctx.createMediaElementSource(audio);
                        const bq = this.ctx.createBiquadFilter();
                        bq.type = 'bandpass';
                        bq.frequency.setValueAtTime(1180, this.ctx.currentTime);
                        bq.Q.setValueAtTime(3.6, this.ctx.currentTime);
                        source.connect(bq);
                        bq.connect(this.ctx.destination);
                    } catch (_) {}
                }
            }

            audio.onplay = () => {
                if (expectedSessionId && this.speakSessionId !== expectedSessionId) return;
                this.isSpeaking = true;
                this.setWaveActive(true);
                this.updateTTSButtonState(true, false);
                if (onStart) onStart();
            };

            audio.onended = () => {
                if (expectedSessionId && this.speakSessionId !== expectedSessionId) return;
                this.isSpeaking = false;
                this.setWaveActive(false);
                this.updateTTSButtonState(false, false);
                this.currentTTSAudio = null;
                if (onEnd) onEnd();
            };

            audio.onerror = () => {
                if (expectedSessionId && this.speakSessionId !== expectedSessionId) return;
                this.currentTTSAudio = null;
                if (textToFallback) {
                    this.speakLocalUtterance(this.cleanSpeechText(textToFallback), speakerType, onStart, onEnd, expectedSessionId);
                } else {
                    this.isSpeaking = false;
                    this.setWaveActive(false);
                    this.updateTTSButtonState(false, false);
                    if (onEnd) onEnd();
                }
            };

            const playPromise = audio.play();
            if (playPromise !== undefined) {
                playPromise.catch(err => {
                    if (err.name === 'AbortError') {
                        // Остановка вызвана намеренным pause() при смене фразы/экрана
                        return;
                    }
                    if (expectedSessionId && this.speakSessionId !== expectedSessionId) return;

                    console.warn('Autoplay prevented by browser:', err);
                    if (!this.unlocked && err.name === 'NotAllowedError' && this.pendingPlayCallbacks) {
                        this.pendingPlayCallbacks.push(() => {
                            if (expectedSessionId && this.speakSessionId !== expectedSessionId) return;
                            audio.play().catch(() => {});
                        });
                    }
                    this.isSpeaking = false;
                    this.setWaveActive(false);
                    this.updateTTSButtonState(false, false);
                    if (onEnd) onEnd();
                });
            }
        } catch (_) {
            this.isSpeaking = false;
            this.setWaveActive(false);
            this.updateTTSButtonState(false, false);
            if (onEnd) onEnd();
        }
    }

    speakLocalUtterance(clean, speakerType = 'male', onStart = null, onEnd = null, expectedSessionId = null) {
        if (expectedSessionId && this.speakSessionId !== expectedSessionId) return;

        if (!this.synth) {
            this.setWaveActive(false);
            this.updateTTSButtonState(false);
            if (onEnd) onEnd();
            return;
        }

        const utter = new SpeechSynthesisUtterance(clean);
        utter.volume = Math.max(0, Math.min(1, this.settings.masterVolume * this.settings.ttsVolume));

        const txtLower = (clean || '').toLowerCase();
        const isBrawler = txtLower.includes('коньяк') || txtLower.includes('бокал') || 
                          txtLower.includes('налей') || txtLower.includes('плачу') || 
                          txtLower.includes('дебош');

        const ruVoices = this.voices.filter(v => (v.lang || '').toLowerCase().startsWith('ru'));
        const isKnownFemaleVoice = (v) => {
            const n = (v.name || '').toLowerCase();
            return n.includes('female') || n.includes('жен') || n.includes('irina') || 
                   n.includes('ирин') || n.includes('elena') || n.includes('елен') || 
                   n.includes('svetlana') || n.includes('светлан') || n.includes('anna') || 
                   n.includes('анн') || n.includes('tatiana') || n.includes('татья') || 
                   n.includes('victor') || n.includes('виктор') || n.includes('olga') || 
                   n.includes('ольг') || n.includes('daria') || n.includes('дарь') || 
                   n.includes('yadviga') || n.includes('ядвиг') || n.includes('alena') || 
                   n.includes('ален') || n.includes('ksenia') || n.includes('ксения');
        };
        const isKnownMaleVoice = (v) => {
            const n = (v.name || '').toLowerCase();
            return n.includes('male') || n.includes('муж') || n.includes('pavel') || 
                   n.includes('павел') || n.includes('dmitry') || n.includes('дмитрий') || 
                   n.includes('aleksandr') || n.includes('александр') || n.includes('boris') || 
                   n.includes('борис') || n.includes('igor') || n.includes('игорь') || 
                   n.includes('yaroslav') || n.includes('ярослав');
        };

        const fVoice = ruVoices.find(isKnownFemaleVoice) || ruVoices[0] || null;
        const mVoice = ruVoices.find(isKnownMaleVoice) || null;

        if (speakerType === 'female') {
            utter.rate = this.settings.ttsRate * 1.05;
            utter.pitch = 1.15;
            if (fVoice) utter.voice = fVoice;
        } else if (speakerType === 'system') {
            utter.rate = 1.18;
            utter.pitch = 1.45; // Роботизированный женский металлический тон
            if (fVoice) utter.voice = fVoice;
            this.playSystemTelemetryBeep();
        } else if (speakerType === 'machinist') {
            utter.rate = 1.05;
            if (mVoice) {
                utter.voice = mVoice;
                utter.pitch = 0.82;
            } else {
                // Если в системе только женский голос (Microsoft Irina), снижаем тон до уверенного баритона рации
                if (fVoice) utter.voice = fVoice;
                utter.pitch = 0.62;
            }
            this.playMachinistRadioChirp();
        } else {
            // speakerType === 'male' (дебошир, пассажир, ревизор и т.д.)
            if (mVoice) {
                utter.voice = mVoice;
                utter.pitch = isBrawler ? 0.75 : 0.88;
                utter.rate = isBrawler ? (this.settings.ttsRate * 0.92) : this.settings.ttsRate;
            } else {
                // Если только женский голос (Irina), питчим вниз до грубого мужского тембра
                if (fVoice) utter.voice = fVoice;
                utter.pitch = isBrawler ? 0.56 : 0.64;
                utter.rate = isBrawler ? (this.settings.ttsRate * 0.90) : (this.settings.ttsRate * 0.95);
            }
        }

        utter.onstart = () => {
            if (expectedSessionId && this.speakSessionId !== expectedSessionId) return;
            this.isSpeaking = true;
            this.setWaveActive(true);
            this.updateTTSButtonState(true, false);
            if (onStart) onStart();
        };

        utter.onend = () => {
            if (expectedSessionId && this.speakSessionId !== expectedSessionId) return;
            this.isSpeaking = false;
            this.setWaveActive(false);
            this.updateTTSButtonState(false, false);
            this.currentUtterance = null;
            if (onEnd) onEnd();
        };

        utter.onerror = () => {
            if (expectedSessionId && this.speakSessionId !== expectedSessionId) return;
            this.isSpeaking = false;
            this.setWaveActive(false);
            this.updateTTSButtonState(false, false);
            this.currentUtterance = null;
            if (onEnd) onEnd();
        };

        this.currentUtterance = utter;
        try {
            this.synth.speak(utter);
        } catch (_) {
            this.isSpeaking = false;
            this.setWaveActive(false);
            this.updateTTSButtonState(false);
            if (onEnd) onEnd();
        }
    }

    stopSpeech() {
        this.speakSessionId = (this.speakSessionId || 0) + 1;
        if (this.currentFetchController) {
            try { this.currentFetchController.abort(); } catch (_) {}
            this.currentFetchController = null;
        }
        if (this.currentTTSAudio) {
            this.currentTTSAudio.onplay = null;
            this.currentTTSAudio.onended = null;
            this.currentTTSAudio.onerror = null;
            try {
                this.currentTTSAudio.pause();
                this.currentTTSAudio.currentTime = 0;
                this.currentTTSAudio.src = '';
            } catch (_) {}
            this.currentTTSAudio = null;
        }
        if (this.synth) {
            try {
                this.synth.cancel();
            } catch (_) {}
        }
        if (this.currentUtterance) {
            this.currentUtterance.onstart = null;
            this.currentUtterance.onend = null;
            this.currentUtterance.onerror = null;
            this.currentUtterance = null;
        }
        this.isSpeaking = false;
        this.setWaveActive(false);
        this.updateTTSButtonState(false);
    }

    toggleSpeechCurrent() {
        if (this.isSpeaking) {
            this.stopSpeech();
            return;
        }

        const el = document.getElementById('card-dialogue-text') || 
                   document.getElementById('vsm-dialogue-text') || 
                   document.querySelector('.vsm-speech-text');
        
        if (el && el.textContent && el.textContent.trim() !== '«...»') {
            this.speak(el.textContent);
        } else {
            this.playClick();
        }
    }

    setWaveActive(active) {
        const waves = document.querySelectorAll('.vsm-speech-audio-wave');
        waves.forEach(w => {
            if (active) w.classList.add('vsm-wave-speaking');
            else w.classList.remove('vsm-wave-speaking');
        });
    }

    updateTTSButtonState(active, loading = false) {
        const btns = document.querySelectorAll('.vsm-tts-play-btn, .vsm-audio-btn, .replay-turn-audio-btn, .vsm-telemetry-audio-btn, .vsm-log-audio-btn');
        btns.forEach(b => {
            const isLog = b.classList.contains('vsm-telemetry-audio-btn') || b.classList.contains('vsm-log-audio-btn');
            const defaultLabel = isLog ? 'Аудио журнала' : 'Аудио';
            const iconSvg = isLog ? 
                '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="18" height="12" x="3" y="6" rx="2"></rect><circle cx="9" cy="12" r="1"></circle><circle cx="15" cy="12" r="1"></circle><path d="M12 2v4"></path></svg>' :
                '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path></svg>';

            if (loading) {
                b.classList.remove('playing');
                b.innerHTML = `
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="vsm-audio-spin">
                        <circle cx="12" cy="12" r="10" stroke-opacity="0.25"></circle>
                        <path d="M12 2a10 10 0 0 1 10 10"></path>
                    </svg>
                    <span>Синтез...</span>
                `;
            } else if (active) {
                b.classList.add('playing');
                b.innerHTML = `
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="5" y="5" width="14" height="14" rx="2"></rect>
                    </svg>
                    <span>Стоп</span>
                `;
            } else {
                b.classList.remove('playing');
                b.innerHTML = `${iconSvg}<span>${defaultLabel}</span>`;
            }
        });
    }

    toggleMute() {
        this.isMuted = !this.isMuted;
        this.updateMuteIcon();
        if (this.isMuted) {
            this.stopSpeech();
            this.stopAmbient();
        } else {
            this.initContext();
            this.playClick();
            if (this.settings.ambientEnabled) this.startAmbient();
        }
        this.syncModalInputs();
        return this.isMuted;
    }

    updateMuteIcon() {
        const btn = document.getElementById('vsm-audio-btn');
        if (!btn) return;
        if (this.isMuted) {
            btn.innerHTML = `
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2">
                    <line x1="1" y1="1" x2="23" y2="23"></line>
                    <path d="M9 9v3a3 3 0 0 0 5.12 2.12M15 9.34V4a3 3 0 0 0-5.94-.6"></path>
                    <path d="M17 16.95A7 7 0 0 1 5 12v-2m14 0v2a7 7 0 0 1-.11 1.23"></path>
                </svg>`;
            btn.style.opacity = '0.65';
            btn.style.borderColor = 'rgba(239, 68, 68, 0.4)';
            btn.title = "Звук выключен (нажмите для открытия настроек)";
        } else {
            btn.innerHTML = `
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
                    <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path>
                </svg>`;
            btn.style.opacity = '1';
            btn.style.borderColor = 'rgba(0, 210, 255, 0.4)';
            btn.title = "Настройки звука и озвучки ВСМ";
        }
    }

    openSettingsModal() {
        this.initContext();
        const modal = document.getElementById('vsm-audio-settings-modal');
        if (!modal) return;
        this.syncModalInputs();
        this.preloader.updateUI();
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
        if (window.lucide) lucide.createIcons();
    }

    closeSettingsModal() {
        const modal = document.getElementById('vsm-audio-settings-modal');
        if (modal) {
            modal.style.display = 'none';
            document.body.style.overflow = '';
        }
        this.saveSettings();
        this.updateMuteIcon();
    }

    syncModalInputs() {
        const setVal = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.value = val;
        };
        const setChecked = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.checked = val;
        };
        const setText = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val;
        };

        // Master
        setChecked('vsm-opt-mute-toggle', !this.isMuted);
        setVal('vsm-opt-master-vol', Math.round(this.settings.masterVolume * 100));
        setText('vsm-val-master-vol', `${Math.round(this.settings.masterVolume * 100)}%`);

        // SFX & Ambient
        setVal('vsm-opt-sfx-vol', Math.round(this.settings.sfxVolume * 100));
        setText('vsm-val-sfx-vol', `${Math.round(this.settings.sfxVolume * 100)}%`);
        setChecked('vsm-opt-chime-toggle', this.settings.chimeEnabled);
        setChecked('vsm-opt-click-toggle', this.settings.clickEnabled);
        setChecked('vsm-opt-warning-toggle', this.settings.warningEnabled);
        setChecked('vsm-opt-ambient-toggle', this.settings.ambientEnabled);
        setVal('vsm-opt-ambient-vol', Math.round(this.settings.ambientVolume * 100));
        setText('vsm-val-ambient-vol', `${Math.round(this.settings.ambientVolume * 100)}%`);

        // TTS
        setChecked('vsm-opt-tts-toggle', this.settings.ttsEnabled);
        setVal('vsm-opt-tts-vol', Math.round(this.settings.ttsVolume * 100));
        setText('vsm-val-tts-vol', `${Math.round(this.settings.ttsVolume * 100)}%`);
        setVal('vsm-opt-tts-rate', this.settings.ttsRate);
        setText('vsm-val-tts-rate', `${this.settings.ttsRate.toFixed(1)}x`);
        setVal('vsm-opt-tts-pitch', this.settings.ttsPitch);
        setText('vsm-val-tts-pitch', `${this.settings.ttsPitch.toFixed(1)}`);

        // Голоса
        setVal('vsm-opt-tts-voice-male', this.settings.ttsVoiceMale);
        setVal('vsm-opt-tts-voice-female', this.settings.ttsVoiceFemale);
        setVal('vsm-opt-tts-voice-system', this.settings.ttsVoiceSystem);
        setVal('vsm-opt-tts-voice-machinist', this.settings.ttsVoiceMachinist);
    }

    testVoice(speakerType) {
        this.initContext();
        let phrase = "Уважаемый проводник, подскажите, когда мы прибываем в Санкт-Петербург?";
        if (speakerType === 'female') {
            phrase = "Здравствуйте! Подскажите, пожалуйста, где находится вагон-бистро скоростного поезда?";
        } else if (speakerType === 'system') {
            phrase = "Внимание. Бортовая система контроля: параметры подвагонного оборудования и буксовых узлов в норме.";
        } else if (speakerType === 'machinist') {
            phrase = "Кабина машиниста на связи. Скорость четыреста километров в час, перегон проходим по графику.";
        }
        this.speak(phrase, null, null, speakerType);
    }

    testSound(key) {
        this.initContext();
        if (key === 'chime') this.playSound('chime', 1.0);
        else if (key === 'click') this.playSound('click', 1.0);
        else if (key === 'success') this.playSound('success', 1.0);
        else if (key === 'warning') this.playSound('warning', 1.0);
        else if (key === 'emergency') this.playSound('emergency', 1.0);
        else if (key === 'door') this.playSound('door', 1.0);
        else if (key === 'ambient') {
            if (this.ambientAudio && !this.ambientAudio.paused) {
                this.stopAmbient();
            } else {
                this.settings.ambientEnabled = true;
                this.saveSettings();
                this.syncModalInputs();
                this.startAmbient();
            }
        }
    }

    async preloadAllNow() {
        this.initContext();
        this.playClick();
        await this.preloader.init();
        if (!this.preloader.isWorking) {
            this.preloader.startWorker();
        }
    }

    async clearTTSCache() {
        this.initContext();
        this.playWarning();
        await this.storage.clearCache();
        this.preloader.loaded = 0;
        this.preloader.updateUI();
    }

    resetDefaults() {
        this.settings = {
            muted: false,
            masterVolume: 0.8,
            sfxVolume: 0.85,
            chimeEnabled: true,
            clickEnabled: true,
            warningEnabled: true,
            ambientEnabled: true,
            ambientVolume: 0.10,
            ttsEnabled: true,
            ttsVolume: 0.9,
            ttsRate: 1.0,
            ttsPitch: 1.0,
            ttsVoiceMale: 'ru-RU-DmitryNeural',
            ttsVoiceFemale: 'ru-RU-SvetlanaNeural',
            ttsVoiceSystem: 'robot-telemetry',
            ttsVoiceMachinist: 'machinist-radio',
            ttsVoice: 'ru-RU-DmitryNeural',
        };
        this.saveSettings();
        this.updateMuteIcon();
        this.syncModalInputs();
        this.playSuccess();
    }
}

window.vsmAudio = new VSMAudioEngine();

document.addEventListener('DOMContentLoaded', () => {
    window.vsmAudio.updateMuteIcon();

    // Проверяем готовность фонового звука по всей платформе ВСМ
    if (window.vsmAudio.settings.ambientEnabled && !window.vsmAudio.isMuted) {
        if (!window.vsmAudio.ambientAudio || window.vsmAudio.ambientAudio.paused) {
            window.vsmAudio.startAmbient();
        }
    }

    const btn = document.getElementById('vsm-audio-btn');
    if (btn) {
        btn.onclick = (e) => {
            e.preventDefault();
            window.vsmAudio.openSettingsModal();
        };
    }
});
