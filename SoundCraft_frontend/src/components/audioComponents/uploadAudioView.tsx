type AudioFileProps = {
    setAudioFile: (file: File | null) => void;
};

export function AudioUploader({ setAudioFile }: AudioFileProps) {
    return (
        <div>
            <input
                type="file"
                accept="audio/*,.mp3,.wav,.flac,.m4a,.mp4,.ogg,.webm"
                onChange={(e) =>
                    setAudioFile(e.target.files?.[0] ?? null)
                }
            />
        </div>
    );
}