import sys
import importlib
import inspect
import pkg_resources
import re

from functools import wraps
from threading import RLock
from git import Repo
from appdirs import user_cache_dir


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
            f'Unsupported module: {name}',
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


def git_clone(url, dir):
    return Repo.clone_from(url=url, to_path=dir)


def get_textlsp_name():
    return 'textLSP'


def get_textlsp_version():
    pkg_resources.require(get_textlsp_name())[0].version


def get_user_cache(app_name=None):
    if app_name is None:
        app_name = get_textlsp_name()
    return user_cache_dir(app_name)


def batch_text(text: str, pattern: re.Pattern, max_size: int, min_size: int = 0):
    sidx = 0
    eidx = max_size
    text_len = len(text)
    while eidx <= text_len:
        matches = list(
            pattern.finditer(
                text[sidx:eidx]
            )
        )
        if len(matches) > 0 and matches[-1].end() > min_size:
            eidx = sidx + matches[-1].end()

        yield text[sidx:eidx]
        sidx = eidx
        eidx = sidx + max_size

    if sidx <= text_len:
        yield text[sidx:text_len]
