import torch


def get_device(use_gpu: bool):
    if isinstance(use_gpu, str):
        return use_gpu

    if use_gpu:
        if torch.cuda.is_available():
            return 'cuda'

        if torch.backends.mps.is_available():
            return 'mps'

    return 'cpu'
