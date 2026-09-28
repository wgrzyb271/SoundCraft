export interface UploadResponse{
    status:"received";
    request_id:string,
    prompt:string;
    filename:string;
}

export interface ProcessingResponse{
    status:"processing";
    request_id:string;
}

export interface CompletedResponse {
status: "completed";
request_id: string;
response: {
    execution_code: "PASSED" | "FAILED";
    error_message?: string | null;
    [key: string]: unknown;
};
}

export type ResultResponse =
| ProcessingResponse
| CompletedResponse;
