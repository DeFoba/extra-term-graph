@echo off
cd %~dp0..
echo Running FULL pipeline...
python run_pipeline.py --step all
pause
