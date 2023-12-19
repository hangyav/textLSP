import sys
import pytest

from multiprocessing import Process

from textLSP import cli
from textLSP.server import SERVER


sys_argv_0 = sys.argv[0]


@pytest.mark.parametrize('args', [
    [sys_argv_0, '-a', '127.0.0.1', '-p', '9999'],
    [sys_argv_0],
])
def test_cli(args):
    sys.argv = args
    p = Process(target=cli.main)
    p.start()
    p.join(1)
    SERVER.shutdown()
    p.join(1)
    p.kill()
