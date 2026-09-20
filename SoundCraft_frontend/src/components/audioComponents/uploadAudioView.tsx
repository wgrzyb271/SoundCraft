import uploadIcon from "../../assets/upload_icon.svg";
import "./styles/uploadAudioView.css";
import "../../fontStylesheet.css"

type AudioFileProps = {
    setAudioFile: (file: File | null) => void;
};

export function AudioUploader({ setAudioFile }: AudioFileProps) {
    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setAudioFile(e.target.files?.[0] ?? null);
    };

    return (
        <div className="audio-upload-div">
            <label className="audio-upload-box" htmlFor="audio-upload">
                <img
                    className="audio-upload-icon"
                    src={uploadIcon}
                    alt=""
                />

                <span className="manrope-regular audio-upload-title">
                    Upload an audio file
                </span>

                <span className="manrope-regular audio-upload-description">
                    here will be supported audio file extensions
                </span>

                <span className="manrope-regular audio-upload-button">
                    Choose file
                </span>

                <input
                    id="audio-upload"
                    type="file"
                    accept="audio/*,.mp3,.wav,.flac,.m4a,.mp4,.ogg,.webm"
                    onChange={handleFileChange}
                />
            </label>
        </div>
    );
}