#!/usr/bin/env bash
# sphinx-build -c docs/source -M html . _build/
# sphinx-apidoc -o docs src/*
ls
sphinx-apidoc -o docs/source src
cd docs || exit
make html