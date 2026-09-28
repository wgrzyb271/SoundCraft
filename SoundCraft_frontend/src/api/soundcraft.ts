import type { UploadResponse } from "./types";

const API_URL = "http://127.0.0.1:8000";

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

export async function getResult(requestId: string) {
    const response = await fetch(
        `${API_URL}/result/${requestId}`
    );

    if (!response.ok) {
        throw new Error(
            `Failed to get result: ${response.status}`
        );
    }

    return response.json();
}

export async function waitForResult(requestId: string,interval = 2000) {
    while (true) {
        const result = await getResult(requestId);

        if (result.status === "completed") {
            return result;
        }

        await new Promise(resolve =>
            setTimeout(resolve, interval)
        );
    }
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