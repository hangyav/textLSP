# textLSP
Language server for text spell and grammar check with various AI tools.

_This tool is in early development._

![textLSP](https://user-images.githubusercontent.com/414596/219856412-8095caa5-9ce6-49fe-9713-78d234837ac4.png)

# Features

## LSP features

* Diagnostics:
    * spelling or grammatical errors
* Code actions:
    * Fix suggestions
    * Analyze paragraph with a selected passive analyzer (if the analyzer does not check on save or change)
        <details><summary>Showcase</summary>
           <img src="https://user-images.githubusercontent.com/414596/219856438-0810eb43-929c-4bc3-811e-2ab53a5b2ae3.gif" height=80% width=80%/>
        </details>
    * Only on the first character of the first line: analyze the whole document if it was not fully checked yet
        <details><summary>Showcase</summary>
           <img src="https://user-images.githubusercontent.com/414596/219856461-406c1e8f-ef71-4b6d-9270-6955320bd6aa.gif" height=80% width=80%/>
        </details>
    * Custom actions defined by a given analyzer
      <details><summary>E.g. OpenAI text generation</summary>
        <img src="https://user-images.githubusercontent.com/414596/219856479-b85b5c2d-6158-44be-9063-12254b76e39c.gif" height=80% width=80%/>
      </details>
* Context based word suggestion
   <details><summary>Showcase</summary>
      <img src="https://user-images.githubusercontent.com/414596/225412142-0cd83321-4a8e-47cf-8b5a-2cec4193800d.gif" height=80% width=80%/>
   </details>

## Analyzers

### Local tools

The following tools run on the local system:

* [LanguageTool](https://languagetool.org): Mainly for development purposes, see [ltex-ls](https://github.com/valentjn/ltex-ls) for a more mature implementation.
* [Gramformer](https://github.com/PrithivirajDamodaran/Gramformer): Neural network based system.
    * Gramformer needs to be installed manually:

      ```pip install git+https://github.com/PrithivirajDamodaran/Gramformer.git```
* hf_checker: Huggingface `text2text-generation` pipline based analyser. See the [flan-t5-large-grammar-synthesis](https://huggingface.co/pszemraj/flan-t5-large-grammar-synthesis) model for an example.
* [hf_completion](https://huggingface.co/docs/transformers/task_summary#language-modeling): Huggingface `fill-mask` pipline based text completion.

### Tools using remote services

**DISCLAIMER: THE RELATED APIS REQUIRE REGISTRATION AND ARE NOT FREE TO USE! USE THESE ANALYZERS ON YOUR OWN RESPONSIBILITY! THE AUTHORS OF TEXTLSP DO NOT ASSUME ANY RESPONSIBILITY FOR THE COSTS INCURRED!**

The following tools use remote text APIs.
Due to potential costs turning off automatic analysis if suggested.

* [OpenAI](https://openai.com/api): Supports text correction as well as text generation through a magic command in the text file.
    <details><summary>Generation showcase</summary>
        <img src="https://user-images.githubusercontent.com/414596/219856479-b85b5c2d-6158-44be-9063-12254b76e39c.gif" height=80% width=80%/>
    </details>
* [GrammarBot](https://rapidapi.com/grammarbot/api/grammarbot): The GrammarBot API provides spelling and grammar checking.

## Supported File Types

* latex
* org
* markdown
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
            -- gramformer dependency needs to be installed manually
            enabled = false,
            gpu = false,
            check_text = {
                on_open = false,
                on_save = true,
                on_change = false,
            }
        },
        hf_checker = {
            enabled = true,
            gpu = false,
            model='pszemraj/flan-t5-large-grammar-synthesis',
            -- model='pszemraj/grammar-synthesis-large',
            min_length=40,
            check_text = {
                on_open = false,
                on_save = true,
                on_change = false,
            }
        },
        hf_completion = {
            enabled = true,
            gpu = false,
            model='bert-base-multilingual-cased',
            topk=5,
        },
        openai = {
            enabled = false,
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
        txt = {
            parse = true,
        },
    },
}
```
