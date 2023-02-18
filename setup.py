import os
from setuptools import setup, find_packages


# Utility function to read the README file.
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="textLSP",
    version="0.1.0",
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
    entry_points = {
        'console_scripts': ['textlsp=textLSP.cli:main'],
    },
    install_requires=[
        'pygls>=1.0.0',
        'lsprotocol>=2022.0.0a9',
        'language-tool-python>=2.7.1',
        'tree_sitter>=0.20.1',
        'gitpython>=3.1.29',
        'appdirs>=1.4.4',
        'torch>=1.13.1',
        'openai>=0.26.4'
    ],
    extras_require={
        'dev': [
            'pytest',
        ]
    },
)
