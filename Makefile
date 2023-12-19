install:
	pip install .

install-development:
	pip install -e .[dev]

install-test:
	pip install .[dev]

uninstall:
	pip uninstall textLSP

test:
	pytest --cov=textLSP
	coverage json
	coverage-threshold --file-line-coverage-min 1 --line-coverage-min 0
