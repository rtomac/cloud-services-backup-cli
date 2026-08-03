import os

def env(**vars: str) -> dict[str, str]:
    return { **os.environ, **vars }

def stringify_args(args : list) -> list[str]:
    return [str(arg) for arg in args]

def flatten_args(params : dict) -> list[str]:
    return [item for kv in params.items() for item in kv]

