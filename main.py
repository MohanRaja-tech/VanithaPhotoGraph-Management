#!/usr/bin/env python3
"""
Face-Based Photo Search & Management System
Main application entry point

Author: AI Assistant
Created: 2025-09-27
"""

import sys
import os
import logging
import tkinter as tk
from tkinter import messagebox
import traceback

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def setup_logging():
    """
    Setup logging configuration.
    """
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.FileHandler('photo_search.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def check_dependencies():
    """
    Check if all required dependencies are installed.
    """
    required_packages = [
        'cv2',
        'face_recognition',
        'PIL',
        'numpy',
        'sqlite3'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'cv2':
                import cv2
            elif package == 'face_recognition':
                import face_recognition
            elif package == 'PIL':
                from PIL import Image, ImageTk
            elif package == 'numpy':
                import numpy
            elif package == 'sqlite3':
                import sqlite3
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        error_msg = f"""Missing required packages: {', '.join(missing_packages)}

Please install them using:
pip install -r requirements.txt

Or install individually:
"""
        for pkg in missing_packages:
            if pkg == 'cv2':
                error_msg += "pip install opencv-python\n"
            elif pkg == 'face_recognition':
                error_msg += "pip install face-recognition\n"
            elif pkg == 'PIL':
                error_msg += "pip install Pillow\n"
            elif pkg == 'numpy':
                error_msg += "pip install numpy\n"
        
        print(error_msg)
        
        # Try to show GUI error if tkinter is available
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Missing Dependencies", error_msg)
        except:
            pass
        
        return False
    
    return True

def check_system_requirements():
    """
    Check system requirements and capabilities.
    """
    warnings = []
    
    # Check Python version
    if sys.version_info < (3, 7):
        warnings.append("Python 3.7 or higher is recommended")
    
    # Check available memory (basic check)
    try:
        import psutil
        memory = psutil.virtual_memory()
        if memory.total < 2 * 1024 * 1024 * 1024:  # 2GB
            warnings.append("At least 2GB RAM is recommended for processing large image collections")
    except ImportError:
        pass
    
    # Check disk space
    try:
        import shutil
        free_space = shutil.disk_usage('.').free
        if free_space < 1024 * 1024 * 1024:  # 1GB
            warnings.append("At least 1GB free disk space is recommended")
    except:
        pass
    
    if warnings:
        warning_msg = "System Warnings:\n" + "\n".join(f"- {w}" for w in warnings)
        logging.warning(warning_msg)
        print(warning_msg)
    
    return True

def main():
    """
    Main application entry point.
    """
    print("Face-Based Photo Search & Management System")
    print("=" * 50)
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Check dependencies
        logger.info("Checking dependencies...")
        if not check_dependencies():
            logger.error("Dependency check failed")
            return 1
        
        # Check system requirements
        logger.info("Checking system requirements...")
        check_system_requirements()
        
        # Import GUI after dependency check
        logger.info("Loading application...")
        from gui_interface import PhotoSearchGUI
        
        # Create and run application
        logger.info("Starting GUI application...")
        app = PhotoSearchGUI()
        app.run()
        
        logger.info("Application closed normally")
        return 0
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        return 0
        
    except Exception as e:
        error_msg = f"Fatal error: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        logger.error(error_msg)
        
        # Try to show GUI error
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Fatal Error", f"Application failed to start:\n\n{str(e)}")
        except:
            print(f"Fatal error: {str(e)}")
        
        return 1

if __name__ == "__main__":
    sys.exit(main())
