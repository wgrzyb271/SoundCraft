from pathlib import Path
from fastapi import UploadFile

import subprocess

async def save_upload(audio:UploadFile,destination:Path)->Path:
    destination.parent.mkdir(parents=True, exist_ok=True)

    with destination.open("wb") as file:
        while chunk:=await audio.read(1024*1024):
            file.write(chunk)
    return destination

def is_real_wav(path:Path)->bool:
    result = subprocess.run(
        ["ffprobe","-v","error","-show_entries","format=format_name","-of",
         "default=noprint_wrappers=1:nokey=1",str(path)],
         capture_output=True,
         text=True
    )
    return result.stdout.strip()=="wav"

def convert_to_wav(input_path:Path, output_path:Path)->Path:
    subprocess.run(
        ["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(input_path),
         "-vn","-ac","2","-ar","44100",str(output_path)],check=True
    )
    return output_path