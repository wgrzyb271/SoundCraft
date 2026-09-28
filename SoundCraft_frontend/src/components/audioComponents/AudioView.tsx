import "./styles/audioView.css";
import { AudioUploader } from "./UploadAudioView";
import { AudioPreview } from "./PreviewAudioView";

type AudioViewProps = { 
    audioFile: File | null;
    setAudioFile: (file: File | null) => void; 
    resultAudioFile: File | null;
    };

export function AudioView({audioFile, setAudioFile, resultAudioFile}:AudioViewProps) {

    return (
        <section className="audio-preview-section">
            {audioFile ? (
                <>
                    <AudioPreview originalAudioFile={audioFile} currentChangesAudioFile={resultAudioFile}></AudioPreview>
                </>
            ) : (
                <AudioUploader setAudioFile={setAudioFile} />
            )}
        </section>
    );
}