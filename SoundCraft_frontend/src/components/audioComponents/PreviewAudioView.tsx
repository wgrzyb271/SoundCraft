import { useEffect, useState } from "react";
import { AudioVisualizer } from "react-audio-visualize";
import AudioPlayer from "react-h5-audio-player";
import "react-h5-audio-player/lib/styles.css";
import './styles/audioPreview.css'
import '../../fontStylesheet.css'
import DownloadIcon from "../../assets/download_icon_w.svg"

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

    const handleDownload = () => {
    if (!currentChangesAudioFile) return;

    const url = URL.createObjectURL(currentChangesAudioFile);

    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = currentChangesAudioFile.name || "soundcraft-audio.wav";

    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();

    URL.revokeObjectURL(url);
};

    return (
        <>
        <div className ="preview-audio-div">
            <fieldset className="audio-div">
                <legend className="audio-div-title manrope-regular">Original audio</legend>
                <div className="audio-center-div">
                    {originalAudioFile && (
                    <div className = "visualizer-wrapper">
                    <AudioVisualizer
                        blob={originalAudioFile}
                        width={750}
                        height={45}
                        barColor={"rgba(240, 240, 240, 0.5)"}
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
            {//TO-DO: CHANGE LATER TO CURRENT AUDIO
            }
            <fieldset className="audio-div current-audio-div">
                <legend className="audio-div-title manrope-regular"> Current audio changes</legend>
               {currentChangesAudioFile && (<button className="download-button" aria-label="Download current audio"
                 title="Download current Audio"onClick={handleDownload}
                >
                     <img src={DownloadIcon} alt="" />
                     </button>)}
                <div className="audio-center-div">
                {currentChangesAudioFile && currentChangesUrl ? (
                    <>
                        <div className = "visualizer-wrapper">
                        <AudioVisualizer
                            blob={currentChangesAudioFile}
                            width={750}
                            height={45}
                            barColor={"rgba(240, 240, 240, 0.5)"}

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
        </div>
        </>
    );
}