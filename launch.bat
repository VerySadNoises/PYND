@echo off
chcp 65001 >nul
cd /d "%~dp0"
python tools/cli.py run examples/demo_part1.yaml
pause
