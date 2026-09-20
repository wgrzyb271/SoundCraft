import { AudioVisualizer } from "react-audio-visualize";

type AudioPreviewProps = {
    originalAudioFile: File | null;
    currentChangesAudioFile: File | null;
};

export function AudioPreview({
    originalAudioFile,
    currentChangesAudioFile,
}: AudioPreviewProps) {
    return (
        <section>
            <div className="original-audio-div">
                {originalAudioFile && (
                    <AudioVisualizer
                        blob={originalAudioFile}
                        width={500}
                        height={75}
                    />
                )}
            </div>

            <div className="current-changes-div">
                {currentChangesAudioFile && (
                    <AudioVisualizer
                        blob={currentChangesAudioFile}
                        width={500}
                        height={75}
                    />
                )}
            </div>
        </section>
    );
}