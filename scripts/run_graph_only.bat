@echo off
cd %~dp0..
echo Re-running Graph step only...
python run_pipeline.py --step graph
pause
