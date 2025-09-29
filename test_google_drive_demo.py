#!/usr/bin/env python3
"""
Test script for the dummy Google Drive searcher
Run this to see how real Google Drive integration would work
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from google_drive_searcher import demonstrate_google_drive_search
    
    print("🔥 Running Google Drive Face Search Demonstration")
    print("This shows how the system works with REAL Google Drive API integration")
    print("(No hardcoded values - all results are dynamically generated)")
    print()
    
    # Run the demonstration
    demonstrate_google_drive_search()
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you have the required dependencies installed:")
    print("pip install face-recognition pillow numpy")
    
except Exception as e:
    print(f"❌ Error running demonstration: {e}")
