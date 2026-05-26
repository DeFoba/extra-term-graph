@echo off
echo Running pipeline in TEST mode (5 articles)...
python run_pipeline.py --step all --max_articles 15
pause
