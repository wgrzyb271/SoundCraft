import { useState } from "react";
import "./styles/audioView.css";
import { AudioUploader } from "./UploadAudioView";
import { AudioPreview } from "./PreviewAudioView";

export function AudioView() {
    const [audioFile, setAudioFile] = useState<File | null>(null);
    const [currentAudioFile, setCurrentAudioFile] = useState<File | null>(null);

    return (
        <section className="audio-preview-section">
            {audioFile ? (
                <>
                    <AudioPreview originalAudioFile={audioFile} currentChangesAudioFile={currentAudioFile}></AudioPreview>
                </>
            ) : (
                <AudioUploader setAudioFile={setAudioFile} />
            )}
        </section>
    );
}