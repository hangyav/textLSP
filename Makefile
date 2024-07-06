install:
	pip install .

install-development:
	pip install -e .[dev,transformers]

install-test:
	pip install .[dev,transformers]

uninstall:
	pip uninstall textLSP

test:
	pytest --cov=textLSP
	coverage json
	coverage-threshold --file-line-coverage-min 1 --line-coverage-min 0
