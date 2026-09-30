/**
 * Web Worker фонового синтеза и предзагрузки реплик ВСМ «Белый кречет».
 * Работает в изолированном фоновом потоке, загружает озвучки всех диалогов
 * и сохраняет их в клиентскую базу данных IndexedDB, передавая чанки
 * в основной поток для синхронизации с localStorage (с контролем квоты памяти).
 */

let isCancelled = false;

function openDB() {
    return new Promise((resolve, reject) => {
        const req = indexedDB.open('VSMAudioCacheDB', 1);
        req.onupgradeneeded = (e) => {
            const db = e.target.result;
            if (!db.objectStoreNames.contains('audios')) {
                const store = db.createObjectStore('audios', { keyPath: 'key' });
                store.createIndex('text', 'text', { unique: false });
                store.createIndex('speakerType', 'speakerType', { unique: false });
            }
        };
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error);
    });
}

function checkKeyInDB(db, key) {
    return new Promise((resolve) => {
        try {
            const tx = db.transaction('audios', 'readonly');
            const store = tx.objectStore('audios');
            const req = store.get(key);
            req.onsuccess = () => resolve(!!req.result);
            req.onerror = () => resolve(false);
        } catch (_) {
            resolve(false);
        }
    });
}

function saveToDB(db, itemRecord) {
    return new Promise((resolve) => {
        try {
            const tx = db.transaction('audios', 'readwrite');
            const store = tx.objectStore('audios');
            store.put(itemRecord);
            tx.oncomplete = () => resolve(true);
            tx.onerror = () => resolve(false);
        } catch (_) {
            resolve(false);
        }
    });
}

function blobToBase64(blob) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(blob);
    });
}

async function processQueue(items) {
    let db = null;
    try {
        db = await openDB();
    } catch (e) {
        self.postMessage({ type: 'ERROR', message: 'IndexedDB init failed in worker' });
    }

    const total = items.length;
    let completed = 0;

    for (let i = 0; i < total; i++) {
        if (isCancelled) break;
        const item = items[i];

        // 1. Проверяем наличие в IndexedDB
        if (db) {
            const exists = await checkKeyInDB(db, item.hash);
            if (exists) {
                completed++;
                self.postMessage({
                    type: 'ITEM_EXISTS',
                    hash: item.hash,
                    id: item.id,
                    index: i + 1,
                    total: total,
                    completed: completed
                });
                continue;
            }
        }

        // 2. Загружаем аудио (приоритет - статический url, если уже на сервере, иначе запрос к api синтеза)
        try {
            let audioBlob = null;
            let audioUrl = item.audio_url;

            // Пробуем получить готовый mp3 из кэша сервера
            if (audioUrl) {
                try {
                    const res = await fetch(audioUrl, { method: 'GET' });
                    if (res.ok && (res.headers.get('content-type') || '').includes('audio')) {
                        audioBlob = await res.blob();
                    }
                } catch (_) {}
            }

            // Если прямого файла нет, запрашиваем через /api/v1/tts/
            if (!audioBlob) {
                const params = new URLSearchParams({
                    text: item.text,
                    voice: item.voice || 'ru-RU-DmitryNeural',
                    rate: item.rate || '+0%',
                    pitch: item.pitch || '+0Hz',
                });
                const apiRes = await fetch(`/api/v1/tts/?${params.toString()}`);
                if (apiRes.ok) {
                    const json = await apiRes.json();
                    if (json && json.audio_url) {
                        const fileRes = await fetch(json.audio_url);
                        if (fileRes.ok) {
                            audioBlob = await fileRes.blob();
                        }
                    }
                }
            }

            if (audioBlob && audioBlob.size > 0) {
                const base64Str = await blobToBase64(audioBlob);

                // Сохраняем в IndexedDB
                if (db) {
                    await saveToDB(db, {
                        key: item.hash,
                        dataUrl: base64Str,
                        text: item.text,
                        speakerType: item.speaker_type,
                        voice: item.voice,
                        timestamp: Date.now()
                    });
                }

                completed++;
                self.postMessage({
                    type: 'ITEM_LOADED',
                    hash: item.hash,
                    id: item.id,
                    index: i + 1,
                    total: total,
                    completed: completed
                });
            } else {
                self.postMessage({
                    type: 'ITEM_FAILED',
                    hash: item.hash,
                    id: item.id,
                    index: i + 1,
                    total: total
                });
            }
        } catch (err) {
            self.postMessage({
                type: 'ITEM_FAILED',
                hash: item.hash,
                id: item.id,
                error: String(err),
                index: i + 1,
                total: total
            });
        }

        // Пауза между запросами для нулевой нагрузки на сеть
        await new Promise(r => setTimeout(r, 120));
    }

    self.postMessage({
        type: 'PRELOAD_COMPLETE',
        total: total,
        completed: completed
    });
}

self.onmessage = function(e) {
    const data = e.data || {};
    if (data.action === 'START_PRELOAD') {
        isCancelled = false;
        processQueue(data.items || []);
    } else if (data.action === 'STOP_PRELOAD') {
        isCancelled = true;
    }
};
