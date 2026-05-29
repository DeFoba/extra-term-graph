"""Wrapper for backward compatibility. Actual code is in modules/web_app.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modules.web_app import app, load_data

if __name__ == "__main__":
    load_data()
    print("=" * 60)
    print("  Extra-Term-Graph Web Interface")
    print("  Open in browser: http://localhost:5000")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=False)
