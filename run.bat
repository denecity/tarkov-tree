@echo off
setlocal enabledelayedexpansion

uv sync
if errorlevel 1 exit /b 1

uv run python src\register_links.py
if errorlevel 1 exit /b 1

uv run python src\scraper.py
if errorlevel 1 exit /b 1

uv run python src\quest_tree.py
if errorlevel 1 exit /b 1

echo Done.
