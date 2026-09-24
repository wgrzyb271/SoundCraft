import { useState } from "react";
import "./styles/audioView.css";
import { AudioUploader } from "./UploadAudioView";
import { AudioPreview } from "./PreviewAudioView";

type AudioViewProps = { audioFile: File | null; setAudioFile: (file: File | null) => void; };

export function AudioView({audioFile, setAudioFile}:AudioViewProps) {
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