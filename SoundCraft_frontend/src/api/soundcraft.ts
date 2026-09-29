import type { ResultResponse, UploadResponse } from "./types";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export async function uploadAudio(audioFile:File, prompt:string):Promise<UploadResponse>{
    const formData = new FormData();
    formData.append("audio",audioFile)
    formData.append("prompt",prompt)
    const response = await fetch(`${API_URL}/upload`,{
        method:"POST",
        body:formData
    });

    if(!response.ok){
        throw new Error(`Upload failed: ${response.status}`)
    }
    return response.json();
}

export async function getResult(requestId: string): Promise<ResultResponse> {
    const response = await fetch(
        `${API_URL}/result/${requestId}/agent_response`
    );

    if (!response.ok) {
        throw new Error(
            `Failed to get result: ${response.status}`
        );
    }

    return response.json();
}

export async function waitForResult(
    requestId: string,
    timeoutMs = 5_400_000
) {
    const websocketUrl = new URL(
        `/ws/result/${encodeURIComponent(requestId)}`,
        API_URL
    );
    websocketUrl.protocol = websocketUrl.protocol === "https:" ? "wss:" : "ws:";

    try {
        await new Promise<void>((resolve, reject) => {
            const socket = new WebSocket(websocketUrl);
            let finished = false;
            const finish = (callback: () => void) => {
                if (finished) return;
                finished = true;
                clearTimeout(timer);
                socket.close();
                callback();
            };
            const timer = window.setTimeout(() => {
                finish(() => reject(new Error("Processing notification timed out")));
            }, timeoutMs);

            socket.onmessage = event => {
                const notice = JSON.parse(event.data) as { status?: string };
                if (notice.status === "completed") {
                    finish(resolve);
                } else if (notice.status === "timeout") {
                    finish(() => reject(new Error("WCSS processing timed out")));
                }
            };
            socket.onerror = () => {
                finish(() => reject(new Error("Completion WebSocket failed")));
            };
            socket.onclose = () => {
                if (!finished) {
                    finish(() => reject(new Error("Completion WebSocket closed unexpectedly")));
                }
            };
        });
    } catch (notificationError) {
        // Jedna próba odzyskania wyniku po awarii/timeout callbacku. Bez pętli
        // i bez cyklicznego otwierania połączeń do WCSS.
        const recovered = await getResult(requestId);
        if (recovered.status === "completed") {
            return recovered;
        }
        throw notificationError;
    }

    const result = await getResult(requestId);
    if (result.status !== "completed") {
        throw new Error("Backend was notified, but the result file is unavailable");
    }
    return result;
}

export async function downloadResultAudio(requestId: string): Promise<File> {

    const response = await fetch(
        `${API_URL}/result/${requestId}/audio`
    );

    if (!response.ok) {
        throw new Error(
            `Failed to download result audio: ${response.status}`
        );
    }

    const blob = await response.blob();

    return new File(
        [blob],
        "result.wav",
        { type: "audio/wav" }
    );
}
