PWD = $(shell pwd)

autofix:
	ruff format .
	ruff check --fix .

check: ruff mypy

ruff:
	ruff format --check .
	ruff check -q .

mypy:
	mypy

test:
	python3 -m pytest

test-ci:
	python3 -m pytest -v

install:
	python3 -m pip install --upgrade -e .

test-requirements:
	python3 -m pip install --upgrade -r test-requirements.txt

clean:
	rm -rf $(PWD)/build $(PWD)/dist $(PWD)/src/mvt.egg-info

dist:
	python3 -m pip install --upgrade build
	python3 -m build

upload:
	python3 -m twine upload dist/*

test-upload:
	python3 -m twine upload --repository testpypi dist/*
