if (Get-Command python3 -ErrorAction SilentlyContinue) {
    $PYTHON = "python3"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PYTHON = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $PYTHON = "py"
} else {
    Write-Error "Python nije pronadjen!"
    exit 1
}


Write-Host "Setting up virtual environment..."
& $PYTHON -m venv .venv
if (Test-Path ".venv\Scripts") {
    .venv\Scripts\Activate.ps1
} elseif (Test-Path ".venv\bin") {
    .venv\bin\Activate.ps1
} else {
    Write-Error "Ne mogu da nadjem venv aktivaciju!"
    exit 1
}

Write-Host "Installing dependencies..."
pip install -e ./api
pip install -e ./platform
pip install -e ./json_plugin
pip install -e ./xml_plugin
pip install -e ./csv_plugin
pip install -e ./simple_visualizer
pip install -e ./block_visualizer

Write-Host "Installing pytest..."
pip install pytest

Write-Host "Running tests..."
pytest api/test_api/
pytest block_visualizer/test_block_visualizer/
pytest csv_plugin/csv_plugin/
pytest json_plugin/json_plugin/
pytest simple_visualizer/test_simple_visualizer/
pytest xml_plugin/xml_plugin/

Write-Host "All tests completed."