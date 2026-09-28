import torch
class ResourceChecker:
    def check(self)->bool:
        return torch.cuda.is_available()