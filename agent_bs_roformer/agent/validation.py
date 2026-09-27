from pathlib import Path
from .audio import STEMS

def validate_output(output_dir:str|Path)->bool:
  output_dir = Path(output_dir)/"audio"
  missing_files = []

  for stem in STEMS:
    output_path = output_dir / f'{stem}.wav'
    if not output_path.exists():
      missing_files.append(str(output_path))
    elif output_path.stat().st_size == 0:
      missing_files.append(f"{output_path} (empty file)") 
  if missing_files:
    raise RuntimeError("Output validation failed. Missing or empty files:\n" + "\n".join(missing_files))
  return True