# textLSP
Language server for text spell and grammar check with various AI tools.

# Install
```
pip install git+https://github.com/hangyav/textLSP
```

# Features

## Supported File Types

* latex
* org
* any other file types as plain text

## LSP features

* Diagnostics: spelling or grammatical errors
* Code actions:
    * Fix suggestions
    * Analyze paragraph with a selected passive analyzer (if the analyzer does not check on save or change)
    * Only on the first character of the first line: analyze the whole document if it was not fully checked yet
    * Custom actions defined by a given analyzer (e.g. prompt OpenAI)

## Analyzers

### Local tools

The following tools run on the local system:

* [LanguageTool](https://languagetool.org): Mainly for development purposes, see [ltex-ls](https://github.com/valentjn/ltex-ls) for a more mature implementation.
* [Gramformer](https://github.com/PrithivirajDamodaran/Gramformer): Neural network based system.

### Tools using remote services

**NOTE: THE RELATED APIS REQUIRE REGISTRATION AND ARE NOT FREE TO USE! USE THESE ANALYZERS ON YOUR OWN RESPONSIBILITY! THE AUTHORS OF TEXTLSP DO NOT ASSUME ANY RESPONSIBILITY FOR THE COSTS INCURRED!**

The following tools use remote text APIs.
Due to potential costs turning off automatic analysis if suggested.

* [OpenAI](https://openai.com/api): Supports text correction and text generation through a magic command in the text file, e.g.:
    * `%OPENAI% Write a sentence about a cat.`
* [GrammarBot](https://rapidapi.com/grammarbot/api/grammarbot): The GrammarBot API provides spelling and grammar checking.
    * TODO: still under development

# Configuration

Example configuration in lua for nvim, other editors should be set up accordingly.

```lua
textLSP = {
    analysers = {
        languagetool = {
            enabled = true,
            check_text = {
                on_open = true,
                on_save = true,
                on_change = false,
            }
        },
        gramformer = {
            enabled = true,
            check_text = {
                on_open = false,
                on_save = true,
                on_change = false,
            }
        },
        openai = {
            enabled = true,
            api_key = '<MY_API_KEY>',
            check_text = {
                on_open = false,
                on_save = false,
                on_change = false,
            },
            -- model = 'text-ada-001',
            model = 'text-babbage-001',
            -- model = 'text-curie-001',
            -- model = 'text-davinci-003',
            edit_model = 'text-davinci-edit-001',
            max_token = 16,
        },
        grammarbot = {
            enabled = false,
            api_key = '<MY_API_KEY>',
            -- longer texts are split, this parameter sets the maximum number of splits per analysis
            input_max_requests = 1,
            check_text = {
                on_open = false,
                on_save = false,
                on_change = false,
            }
        },
    },
    documents = {
        org = {
            org_todo_keywords = {
                'TODO',
                'IN_PROGRESS',
                'DONE'
            },
        },
    },
}
```
