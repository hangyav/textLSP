import pytest
import copy

from pygls.protocol import default_converter

from tests.lsp_test_client import session, defaults


@pytest.fixture
def json_converter():
    return default_converter()


@pytest.fixture
def simple_server():
    with session.LspSession() as lsp_session:
        lsp_session.initialize()
        yield lsp_session


@pytest.fixture
def langtool_ls():
    init_params = copy.deepcopy(defaults.VSCODE_DEFAULT_INITIALIZE)
    init_params["initializationOptions"] = {
        'textLSP': {
            'analysers': {
                'languagetool': {
                    'enabled': True,
                    'check_text': {
                        'on_open': True,
                        'on_save': True,
                        'on_change': True,
                    }
                }
            }
        }
    }

    with session.LspSession() as lsp_session:
        lsp_session.initialize(init_params)

        yield lsp_session


@pytest.fixture
def langtool_ls_onsave():
    init_params = copy.deepcopy(defaults.VSCODE_DEFAULT_INITIALIZE)
    init_params["initializationOptions"] = {
        'textLSP': {
            'analysers': {
                'languagetool': {
                    'enabled': True,
                    'check_text': {
                        'on_open': True,
                        'on_save': True,
                        'on_change': False,
                    }
                }
            }
        }
    }

    with session.LspSession() as lsp_session:
        lsp_session.initialize(init_params)

        yield lsp_session
