import './styles/audioView.css'
import { AudioUploader } from './UploadAudioView'
import { AudioPreview } from './PreviewAudioView'

type AudioViewProps = {
  audioFile: File | null
  resultAudioFile: File | null
  onAudioSelected: (file: File) => void
}

export function AudioView({ audioFile, resultAudioFile, onAudioSelected }: AudioViewProps) {
  return (
    <section className="audio-preview-section">
      {audioFile ? (
        <AudioPreview
          originalAudioFile={audioFile}
          currentChangesAudioFile={resultAudioFile}
        />
      ) : (
        <AudioUploader onAudioSelected={onAudioSelected} />
      )}
    </section>
  )
}
