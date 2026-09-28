from pathlib import Path
import sys
import torch
import yaml 

def load_config(config_path:str|Path)->dict:
    config_path = Path(config_path)
    with open(config_path,"r") as f:
        return yaml.load(f, Loader=yaml.FullLoader)

def load_model(config_path:str|Path, checkpoint_path:str|Path,repo_path:str|Path):
    config = load_config(config_path)
    repo_path = str(Path(repo_path))

    if repo_path not in sys.path:
        sys.path.insert(0,repo_path)
    
    from models.bs_roformer.bs_roformer import BSRoformer

    model_config = config["model"]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model = BSRoformer(**model_config)
    checkpoint = torch.load(checkpoint_path,map_location="cpu")

    if isinstance(checkpoint, dict) and "state_dict" in checkpoint:
        state_dict = checkpoint["state_dict"]
    else:
        state_dict = checkpoint
        
    model.load_state_dict(state_dict, strict=True)
    model = model.to(device)
    model.eval()

    return model, device, config


