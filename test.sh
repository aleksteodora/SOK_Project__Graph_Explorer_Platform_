#!/bin/bash

set -e

echo "Setting up virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "Installing dependencies..."
pip install -e ./api
pip install -e ./platform
pip install -e ./json_plugin
pip install -e ./xml_plugin
pip install -e ./csv_plugin
pip install -e ./simple_visualizer
pip install -e ./block_visualizer

echo "Installing pytest..."
pip install pytest

echo "Running tests..."
pytest api/test_api/
pytest block_visualizer/test_block_visualizer/
pytest csv_plugin/csv_plugin/
pytest json_plugin/json_plugin/
pytest simple_visualizer/test_simple_visualizer/
pytest xml_plugin/xml_plugin/

echo "All tests completed."