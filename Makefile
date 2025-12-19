PWD = $(shell pwd)

check: ruff mypy

ruff:
	ruff check .

mypy:
	mypy

test:
	python3 -m pytest

test-ci:
	python3 -m pytest -v

install:
	python3 -m pip install --upgrade -e .

test-requirements:
	python3 -m pip install --upgrade --group dev

generate-proto-parsers:
	# Generate python parsers for protobuf files
	PROTO_FILES=$$(find src/mvt/android/parsers/proto/ -iname "*.proto"); \
	protoc -Isrc/mvt/android/parsers/proto/ --python_betterproto_out=src/mvt/android/parsers/proto/ $$PROTO_FILES

clean:
	rm -rf $(PWD)/build $(PWD)/dist $(PWD)/src/mvt.egg-info

dist:
	python3 -m pip install --upgrade build
	python3 -m build

upload:
	python3 -m twine upload dist/*

test-upload:
	python3 -m twine upload --repository testpypi dist/*
