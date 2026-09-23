import { useEffect, useState } from "react";
import { AudioVisualizer } from "react-audio-visualize";
import AudioPlayer from "react-h5-audio-player";
import "react-h5-audio-player/lib/styles.css";
import './styles/audioPreview.css'
import '../../fontStylesheet.css'

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
        <>
            <fieldset className="audio-div">
                <legend className="audio-div-title manrope-regular">Original audio</legend>
                <div className="audio-center-div">
                    {originalAudioFile && (
                    <div className = "visualizer-wrapper">
                    <AudioVisualizer
                        blob={originalAudioFile}
                        width={750}
                        height={75}
                        barColor={"rgba(221, 221, 221, 0.5)"}
                    />
                    </div>
                )}

                {originalAudioUrl && (
                    <AudioPlayer
                        autoPlay={false}
                        src={originalAudioUrl}
                        showFilledVolume={true}
                        onPlay={() => console.log("onPlay")
                        }
                    />
                )}

                </div>
            </fieldset>

            <fieldset className="audio-div">
                <legend className="audio-div-title manrope-regular"> Current audio changes</legend>
                <div className="audio-center-div">
                {currentChangesAudioFile && currentChangesUrl ? (
                    <>
                        <div className = "visualizer-wrapperr">
                        <AudioVisualizer
                            blob={currentChangesAudioFile}
                            width={750}
                            height={75}
                        />
                        </div>
                        <AudioPlayer
                            autoPlay={false}
                            src={currentChangesUrl}
                            showFilledVolume={true}
                            onPlay={() => console.log("onPlay")}
                        />
                    </>
                ) : (
                    <div className ="current-audio-disclaimer-div">
                    <p className = "current-audio-disclaimer-p manrope-light">No current changes to display</p>
                    <p className = "current-audio-disclaimer-p manrope-light"> Make an adjustment to the audio to see the updated waveform here.</p>
                    </div>
                )}
                </div>
            </fieldset>
        </>
    );
}