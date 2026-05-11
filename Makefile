PWD = $(shell pwd)
UV ?= uv

check: ruff mypy

ruff:
	$(UV) run ruff check .

mypy:
	$(UV) run mypy

test:
	$(UV) run pytest

test-ci:
	$(UV) run pytest -v

install:
	$(UV) sync

test-requirements:
	$(UV) sync --group dev

generate-proto-parsers:
	# Generate python parsers for protobuf files
	PROTO_FILES=$$(find src/mvt/android/parsers/proto/ -iname "*.proto"); \
	$(UV) run protoc -Isrc/mvt/android/parsers/proto/ --python_betterproto2_out=src/mvt/android/parsers/proto/ $$PROTO_FILES

clean:
	rm -rf $(PWD)/build $(PWD)/dist $(PWD)/src/mvt.egg-info

dist:
	$(UV) build

upload:
	$(UV) tool run twine upload dist/*

test-upload:
	$(UV) tool run twine upload --repository testpypi dist/*
