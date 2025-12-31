# textLSP

Language server for text spell and grammar check with various AI tools.

_This tool is in early development._

![textLSP](https://user-images.githubusercontent.com/414596/219856412-8095caa5-9ce6-49fe-9713-78d234837ac4.png)

## Features

### LSP features

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
* [Ollama](https://www.ollama.com): Run LLMs efficiently on your local machine.
        It supports diagnostics, code actions and prompt based text generation.
    * Ollama needs to be [installed manually](https://www.ollama.com/download) first.
    * Various [LLMs](https://www.ollama.com/library) are supported, such as `Llama 3`, `Gemma` or `Mixtra`. Suggested model is `Phi3`, due to its speed, size and accuracy.
* hf_checker: Huggingface `text2text-generation` pipeline based analyser. See the [flan-t5-large-grammar-synthesis](https://huggingface.co/pszemraj/flan-t5-large-grammar-synthesis) model for an example.
   <details><summary>Models</summary>
      <ul>
       <li>pszemraj/grammar-synthesis-small</li>
       <li>pszemraj/grammar-synthesis-large</li>
       <li>pszemraj/flan-t5-large-grammar-synthesis</li>
       <li>pszemraj/flan-t5-xl-grammar-synthesis</li>
       <li>pszemraj/bart-base-grammar-synthesis</li>
      </ul>
   </details>
* hf_instruction_checker: Huggingface `text2text-generation` pipeline based
analyser using instruction tuned models. See the Grammarly's
[CoEdIT](https://github.com/vipulraheja/coedit) model for an example. Supports
error checking and text generation, such as paraphrasing, through the `%HF%`
magic command (see the OpenAI analyser below).
   <details><summary>Models</summary>
      <ul>
       <li>grammarly/coedit-large</li>
       <li>grammarly/coedit-xl</li>
       <li>grammarly/coedit-xl-composite</li>
       <li>grammarly/coedit-xxl</li>
       <li>jbochi/coedit-base</li>
       <li>jbochi/coedit-small</li>
       <li>jbochi/candle-coedit-quantized</li>
      </ul>
   </details>
* [hf_completion](https://huggingface.co/docs/transformers/task_summary#language-modeling): Huggingface `fill-mask` pipeline based text completion.
* [Gramformer](https://github.com/PrithivirajDamodaran/Gramformer): Neural network based system.

### Tools using remote services

**DISCLAIMER: THE RELATED APIS REQUIRE REGISTRATION AND ARE NOT FREE TO USE! USE THESE ANALYZERS ON YOUR OWN RESPONSIBILITY! THE AUTHORS OF TEXTLSP DO NOT ASSUME ANY RESPONSIBILITY FOR THE COSTS INCURRED!**

The following tools use remote text APIs.
Due to potential costs turning off automatic analysis if suggested.

* [OpenAI](https://openai.com/api): Supports text correction as well as text generation through a magic command in the text file.
  * A custom URL can be set to use an OpenAI-compatible server. See the example
        [configuration](#configuration) below.

    <details><summary>Generation showcase</summary>
        <img src="https://user-images.githubusercontent.com/414596/219856479-b85b5c2d-6158-44be-9063-12254b76e39c.gif" height=80% width=80%/>
    </details>
* [GrammarBot](https://rapidapi.com/grammarbot/api/grammarbot): The GrammarBot API provides spelling and grammar checking.

## Supported File Types

* latex
* org
* markdown
* any other file types as plain text

## Setup

### Install
```
pip install textLSP
```

For the latest version:
```
pip install git+https://github.com/hangyav/textLSP
```

#### Additional dependencies
Some analyzers need additional dependencies!

* hf_checker, hf_instruction_checker and hf_completion:
```
pip install textLSP[transformers]
```

* Gramformer needs to be installed manually:
```
pip install git+https://github.com/PrithivirajDamodaran/Gramformer.git
```

### Running
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

### Configuration

Using textLSP within an editor depends on the editor of choice.
For a few examples how to set up language servers in general in some of the popular editors see [here](https://github.com/openlawlibrary/pygls/tree/master/examples/hello-world#editor-configurations) or take a look at the related documentation of your editor.

By default, all analyzers are disabled in textLSP, they have to be turned on in the settings.
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
        ollama = {
          enabled = true,
          check_text = {
            on_open = false,
            on_save = true,
            on_change = false,
          },
          model = "gemma3:4b",  -- more accurate
          -- model = "gemma3:1b",  -- smaller but faster model
          max_token = 50,
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
            enabled = false,
            gpu = false,
            quantize=32,
            model='pszemraj/flan-t5-large-grammar-synthesis',
            min_length=40,
            check_text = {
                on_open = false,
                on_save = true,
                on_change = false,
            }
        },
        hf_instruction_checker = {
            enabled = false,
            gpu = false,
            quantize=32,
            model='grammarly/coedit-large',
            min_length=40,
            check_text = {
                on_open = false,
                on_save = true,
                on_change = false,
            }
        },
        hf_completion = {
            enabled = false,
            gpu = false,
            quantize=32,
            model='bert-base-multilingual-cased',
            topk=5,
        },
        openai = {
            enabled = false,
            api_key = '<MY_API_KEY>',
            -- url = '<CUSTOM_URL>'  -- optional to use an OpenAI-compatible server
            check_text = {
                on_open = false,
                on_save = false,
                on_change = false,
            },
            model = 'gpt-5-nano',
            max_token = 100,
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
        -- the language of the documents, could be set to `auto` of `auto:<fallback>`
        -- to detect automatically, default: auto:en
        language = "auto:en",
        -- do not autodetect documents with fewer characters
        min_length_language_detect = 20,
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
