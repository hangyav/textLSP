from textLSP.types import ConfigurationError

try:
    import torch
except ModuleNotFoundError:
    raise ConfigurationError(
        "Dependencies are missing for torch-based modules. Please look at textLSP's"
        " documentation for installing additional dependencies."
    )

def get_device(use_gpu: bool):
    if isinstance(use_gpu, str):
        return use_gpu

    if use_gpu:
        if torch.cuda.is_available():
            return 'cuda'

        if torch.backends.mps.is_available():
            return 'mps'

    return 'cpu'


def set_quantization_args(bits, device, model_kwargs):
    if bits not in {4, 8, 16, 32}:
        raise ConfigurationError(f'Invalid quantization value: {bits}.'
                                 ' Supported: 4, 8, 16, 32.')

    if bits == 16:
        model_kwargs['torch_dtype'] = torch.bfloat16
    elif bits == 4 or bits == 8:
        if device != 'cuda':
            raise ConfigurationError(f'{bits}bit quantization needs CUDA GPU.')
        else:
            model_kwargs[f'load_in_{bits}bit'] = True

    return model_kwargs
