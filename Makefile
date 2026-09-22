.PHONY: install tour quickstart test build

install:
	python3 -m pip install -e .

tour:
	scopedact tour

quickstart:
	python3 examples/quickstart.py

test:
	python3 -m unittest discover -s tests -v

build:
	python3 -m build
