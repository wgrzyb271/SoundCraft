import { useState } from "react";
import "./styles/audioView.css";
import { AudioUploader } from "./uploadAudioView";
import { AudioPreview } from "./previewAudioView";

export function AudioView() {
    const [audioFile, setAudioFile] = useState<File | null>(null);

    return (
        <section className="audio-preview-section">
            {audioFile ? (
                <>
                    <AudioPreview originalAudioFile={audioFile} currentChangesAudioFile={null}></AudioPreview>
                </>
            ) : (
                <AudioUploader setAudioFile={setAudioFile} />
            )}
        </section>
    );
}