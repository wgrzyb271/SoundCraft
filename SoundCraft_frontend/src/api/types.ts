export interface UploadAudioResponse{
    status:"received";
    request_id:string,
    file_name:string;
}

export interface UploadPromptResponse{
    status:"received";
    request_id:string,
    prompt:string;
}

export interface ProcessingResponse{
    status:"processing"
}

export interface CompletedResponse {
status: "completed";
request_id: string;
response: Record<string, unknown>;
}

export type ResultResponse =
| ProcessingResponse
| CompletedResponse;