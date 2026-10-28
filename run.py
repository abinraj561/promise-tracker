"""
Promise Tracker - Application Server Runner
Starts the Uvicorn ASGI server and serves the Promise Tracker web app.
"""

import sys
import os
import uvicorn

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  [PROMISE TRACKER] What did we tell customers we would do?")
    print("="*60)
    print("  >> Server URL: http://127.0.0.1:8855")
    print("  >> Live WhatsApp & AI Promise Extractor: READY")
    print("  >> Microsoft Teams & Morning Dispatch: READY")
    print("="*60 + "\n")
    
    uvicorn.run("main:app", host="127.0.0.1", port=8855, reload=False)
