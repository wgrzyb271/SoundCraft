import type { UploadAudioResponse, UploadPromptResponse } from "./types";

const API_URL = "http://127.0.0.1:8000";

export async function uploadAudio(audioFile:File):Promise<UploadAudioResponse>{
    const formData = new FormData();
    formData.append("audio",audioFile)
    //formData.append("prompt",prompt)
    const response = await fetch(`${API_URL}/upload/audio/`,{
        method:"POST",
        body:formData
    });

    if(!response.ok){
        throw new Error(`Audio upload failed: ${response.status}`)
    }
    return response.json();
}
export async function uploadPrompt(request_id:string,prompt:string):Promise<UploadPromptResponse>{
    const formData = new FormData();
    formData.append("prompt",prompt)
    const response = await fetch(`${API_URL}/upload/${request_id}/prompt`,{
        method:"POST",
        body:formData
    });
    if (!response.ok) {
        throw new Error(`Prompt upload failed: ${response.status}`)
    }
    return response.json();

}
export async function getAgentResponse(requestId: string) {
    const response = await fetch(
        `${API_URL}/result/${requestId}/agent_reponse`
    );

    if (!response.ok) {
        throw new Error(
            `Failed to get result: ${response.status}`
        );
    }

    return response.json();
}

export function connectToResult(requestId:string):Promise<void>{
    return new Promise((resolve, reject)=>{
        const socket = new WebSocket(`ws://127.0.0.1:8000/ws/${requestId}`);

        socket.onopen=()=>{console.log("WebSocket connected: ", requestId)}
        socket.onmessage = (event)=>{
            const message = JSON.parse(event.data)
            console.log("WS message: ", message);
            if (message.type ==="completed"){
                socket.close()
                resolve()
            }
        };
        socket.onerror=(error)=>{
            console.error("Websocket error:",error)
            socket.close()
            reject(error);
        };
        socket.onclose=()=>{
            console.log("Websocket closed");
        }
    })
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