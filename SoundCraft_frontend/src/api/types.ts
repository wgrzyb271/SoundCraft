export interface UploadResponse{
    status:"received";
    request_id:string,
    prompt:string;
    file_name:string;
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