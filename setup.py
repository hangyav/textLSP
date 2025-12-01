import os
from setuptools import setup, find_packages


# Utility function to read the README file.
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="textLSP",
    version="0.3.2",
    author="Viktor Hangya",
    author_email="hangyav@gmail.com",
    description=("Language server for text spell and grammar check with various tools."),
    license="GPLv3",
    url="https://github.com/hangyav/textLSP",
    packages=find_packages(include=['textLSP*']),
    long_description=read('README.md'),
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    entry_points={
        'console_scripts': ['textlsp=textLSP.cli:main'],
    },
    install_requires=[
        'pygls==2.0.0',
        'lsprotocol==2025.0.0',
        'language-tool-python==3.1.0',
        'tree_sitter==0.21.3',
        'gitpython==3.1.45',
        'appdirs==1.4.4',
        'openai==2.8.1',
        'sortedcontainers==2.4.0',
        'langdetect==1.0.9',
        'ollama==0.6.1',
    ],
    extras_require={
        'dev': [
            'pytest==9.0.1',
            'python-lsp-jsonrpc==1.1.2',
            'pytest-cov==7.0.0',
            'coverage-threshold==0.6.2'
        ],
        'transformers': [
            'torch==2.9.1',
            'transformers==4.57.3',
            'bitsandbytes==0.48.2',
        ],
    },
)
