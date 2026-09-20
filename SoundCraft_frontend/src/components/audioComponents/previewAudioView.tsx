import { AudioVisualizer } from "react-audio-visualize"
import { useRef } from "react"
type AudioPrevProps = {
    originalAudioFile:  File | null;
    currentChangesAudioFile :  File | null;
}

export function AudioPreview({originalAudioFile, currentChangesAudioFile}:AudioPrevProps){
const originalVisualizerRef = useRef<HTMLCanvasElement>(null);
const changesVisualizerRef = useRef<HTMLCanvasElement>(null);

    return (<section>
        <div className="original-audio-div">
            {originalAudioFile && (
                <AudioVisualizer ref={originalVisualizerRef} blob={originalAudioFile}
                  width={500}
                height={75}
                ></AudioVisualizer>
            )}
        </div>
        <div className="current-changes-div">
                        {currentChangesAudioFile && (
                <AudioVisualizer ref={changesVisualizerRef} blob={currentChangesAudioFile}
                  width={500}
                height={75}
                ></AudioVisualizer>
            )}
        </div>
    </section>)
}