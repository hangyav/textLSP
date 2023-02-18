# textLSP
Language server for text spell and grammar check with various AI tools.

_This tool is in early development._

![textLSP](https://github.com/hangyav/textLSP/raw/main/images/textLSP.png)

# Features

## LSP features

* Diagnostics: spelling or grammatical errors
* Code actions:
    * Fix suggestions
    * Analyze paragraph with a selected passive analyzer (if the analyzer does not check on save or change)
        <details><summary>Showcase</summary>
            <script async id="asciicast-Vr8OqiC7uOtXt46mDWCS75Fvp" src="https://asciinema.org/a/Vr8OqiC7uOtXt46mDWCS75Fvp.js"></script>
        </details>
    * Only on the first character of the first line: analyze the whole document if it was not fully checked yet
        <details><summary>Showcase</summary>
            <script async id="asciicast-GtlfiXgm0ei9A4fTzwr6ERtXi" src="https://asciinema.org/a/GtlfiXgm0ei9A4fTzwr6ERtXi.js"></script>
        </details>

    * Custom actions defined by a given analyzer (e.g. prompt OpenAI)

## Analyzers

### Local tools

The following tools run on the local system:

* [LanguageTool](https://languagetool.org): Mainly for development purposes, see [ltex-ls](https://github.com/valentjn/ltex-ls) for a more mature implementation.
* [Gramformer](https://github.com/PrithivirajDamodaran/Gramformer): Neural network based system.

### Tools using remote services

**DISCLAIMER: THE RELATED APIS REQUIRE REGISTRATION AND ARE NOT FREE TO USE! USE THESE ANALYZERS ON YOUR OWN RESPONSIBILITY! THE AUTHORS OF TEXTLSP DO NOT ASSUME ANY RESPONSIBILITY FOR THE COSTS INCURRED!**

The following tools use remote text APIs.
Due to potential costs turning off automatic analysis if suggested.

* [OpenAI](https://openai.com/api): Supports text correction as well as text generation through a magic command in the text file.
    <details><summary>Generation showcase</summary>
        <script async id="asciicast-Zdln0mCeh9nihyzZNOlcyuxLO" src="https://asciinema.org/a/Zdln0mCeh9nihyzZNOlcyuxLO.js"></script>
    </details>
* [GrammarBot](https://rapidapi.com/grammarbot/api/grammarbot): The GrammarBot API provides spelling and grammar checking.

## Supported File Types

* latex
* org
* any other file types as plain text

# Setup

## Install
```
pip install textLSP
```

For the latest version:
```
pip install git+https://github.com/hangyav/textLSP
```

## Running
Simply run:
```
textlsp
```

Since some analyzers are computation intensive, consider running it on a server using the TCP interface:
```
textlsp --address 0.0.0.0 --port 1234
```
or simply over ssh (with ssh key) if the client doesn't support it:
```
ssh <server> textlsp
```

## Configuration

Using textLSP within an editor depends on the editor of choice.
For a few examples how to setup language servers in general in some of the popular editors see [here](https://github.com/openlawlibrary/pygls/tree/master/examples/hello-world#editor-configurations) or take a look at the related documentation of your editor.

By default all analyzers are disabled in textLSP, they have to be turned on in the settings.
Example configuration in lua for nvim (other editors should be set up accordingly):

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
            gpu = false,
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
