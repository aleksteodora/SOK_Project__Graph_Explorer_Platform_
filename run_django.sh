#!/bin/bash
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
elif command -v py &> /dev/null; then
    PYTHON=py
else
    echo "Python nije pronadjen!"
    exit 1
fi

$PYTHON -m venv .venv

if [ -d ".venv/Scripts" ]; then
    source .venv/Scripts/activate
elif [ -d ".venv/bin" ]; then
    source .venv/bin/activate
else
    echo "Ne mogu da nadjem venv aktivaciju!"
    exit 1
fi

pip install ./api
pip install ./platform
pip install ./csv_plugin
pip install ./json_plugin
pip install ./xml_plugin
pip install ./simple_visualizer
pip install ./block_visualizer

$PYTHON ./django/manage.py migrate
$PYTHON ./django/manage.py runserver