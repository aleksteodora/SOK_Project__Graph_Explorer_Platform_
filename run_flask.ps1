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

& $PYTHON -m venv .venv

if (Test-Path ".venv\Scripts") {
    .venv\Scripts\Activate.ps1
} elseif (Test-Path ".venv\bin") {
    .venv\bin\Activate.ps1
} else {
    Write-Error "Ne mogu da nadjem venv aktivaciju!"
    exit 1
}

pip install .\api
pip install .\platform
pip install .\csv_plugin
pip install .\json_plugin
pip install .\xml_plugin
pip install .\simple_visualizer
pip install .\block_visualizer

& $PYTHON .\flask\app.py