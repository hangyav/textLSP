import os
import sys
from setuptools import setup, find_packages

if sys.version_info >= (3, 12, 0):
    # due to current pytorch limitations
    print('Required python version <= 3.12.0')
    sys.exit(-1)


# Utility function to read the README file.
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="textLSP",
    version="0.2.1",
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
        'pygls==1.2.0',
        'lsprotocol==2023.0.0',
        'language-tool-python==2.7.1',
        'tree_sitter==0.20.4',
        'gitpython==3.1.40',
        'appdirs==1.4.4',
        'torch==2.1.1',
        'openai==1.3.5',
        'transformers==4.35.2',
        'sortedcontainers==2.4.0',
    ],
    extras_require={
        'dev': [
            'pytest==7.4.3',
            'python-lsp-jsonrpc==1.1.2',
        ]
    },
)
