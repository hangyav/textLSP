import sys
import importlib
import inspect

from functools import wraps
from threading import RLock


def merge_dicts(dict1, dict2):
    for key in dict2:
        if key in dict1 and isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
            merge_dicts(dict1[key], dict2[key])
        else:
            dict1[key] = dict2[key]
    return dict1


def get_class(name, cls_type, return_multi=False):
    try:
        module = importlib.import_module(name)
    except ModuleNotFoundError:
        raise ModuleNotFoundError(
            f'Unsupported analyser: {name}',
        )

    cls_lst = list()
    for cls_name, obj in inspect.getmembers(
            sys.modules[module.__name__],
            inspect.isclass
    ):
        if obj != cls_type and issubclass(obj, cls_type):
            if not return_multi and len(cls_lst) > 0:
                raise ImportError(
                    f'There are multiple implementations of {name}. This is an'
                    ' implementation error. Please report this issue!'
                )
            cls_lst.append(obj)

    if len(cls_lst) == 0:
        raise ImportError(
            f'There is no implementation of {name}. This is an implementation'
            ' error. Please report this issue!',
        )

    return cls_lst if return_multi else cls_lst[0]


def synchronized(wrapped):
    lock = RLock()

    @wraps(wrapped)
    def _wrapper(*args, **kwargs):
        with lock:
            return wrapped(*args, **kwargs)
    return _wrapper
