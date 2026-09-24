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