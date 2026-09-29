import uploadIcon from "../../assets/upload_icon.svg";
import "./styles/uploadAudioView.css";
import "../../fontStylesheet.css"

type AudioFileProps = {
    onAudioSelected: (file: File) => void;
};

export function AudioUploader({ onAudioSelected }: AudioFileProps) {
    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if(file){
            onAudioSelected(file)
            console.log("AUDIO ADDED")
        }
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
                    Supported audio file extensions are: .mp3, .wav, .flac, .m4a, .mp4, .ogg, .webm
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