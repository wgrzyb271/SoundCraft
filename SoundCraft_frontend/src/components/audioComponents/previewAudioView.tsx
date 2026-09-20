import { useEffect, useState } from "react";
import { AudioVisualizer } from "react-audio-visualize";
import AudioPlayer from "react-h5-audio-player";
import "react-h5-audio-player/lib/styles.css";

type AudioPreviewProps = {
    originalAudioFile: File | null;
    currentChangesAudioFile: File | null;
};

export function AudioPreview({
    originalAudioFile,
    currentChangesAudioFile,
}: AudioPreviewProps) {
    const [originalAudioUrl, setOriginalAudioUrl] = useState<string | null>(null);
    const [currentChangesUrl, setCurrentChangesUrl] = useState<string | null>(null);

    // Original audio URL
    useEffect(() => {
        if (!originalAudioFile) {
            setOriginalAudioUrl(null);
            return;
        }

        const url = URL.createObjectURL(originalAudioFile);
        setOriginalAudioUrl(url);

        return () => {
            URL.revokeObjectURL(url);
        };
    }, [originalAudioFile]);

    // Current/changed audio URL
    useEffect(() => {
        if (!currentChangesAudioFile) {
            setCurrentChangesUrl(null);
            return;
        }

        const url = URL.createObjectURL(currentChangesAudioFile);
        setCurrentChangesUrl(url);

        return () => {
            URL.revokeObjectURL(url);
        };
    }, [currentChangesAudioFile]);

    return (
        <section>
            {/* Original audio */}
            <div className="audio-div">
                {originalAudioFile && (
                    <AudioVisualizer
                        blob={originalAudioFile}
                        width={750}
                        height={75}
                    />
                )}

                {originalAudioUrl && (
                    <AudioPlayer
                        autoPlay={false}
                        src={originalAudioUrl}
                        onPlay={() => console.log("onPlay")}
                    />
                )}
            </div>

            {/* Current changes */}
            <div className="audio-div">
                {currentChangesAudioFile && currentChangesUrl ? (
                    <>
                        <AudioVisualizer
                            blob={currentChangesAudioFile}
                            width={750}
                            height={75}
                        />

                        <AudioPlayer
                            autoPlay={false}
                            src={currentChangesUrl}
                            onPlay={() => console.log("onPlay")}
                        />
                    </>
                ) : (
                    <p>No current changes to display</p>
                )}
            </div>
        </section>
    );
}