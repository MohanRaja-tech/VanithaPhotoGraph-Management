#!/usr/bin/env python3
"""
Test script to verify the Face-Based Photo Search & Management System installation
"""

import sys
import os
import traceback

def test_imports():
    """Test if all required modules can be imported."""
    print("Testing imports...")
    
    try:
        import cv2
        print(f"✓ OpenCV version: {cv2.__version__}")
    except ImportError as e:
        print(f"✗ OpenCV import failed: {e}")
        return False
    
    try:
        import face_recognition
        print("✓ face_recognition imported successfully")
    except ImportError as e:
        print(f"✗ face_recognition import failed: {e}")
        return False
    
    try:
        from PIL import Image, ImageTk
        print(f"✓ Pillow version: {Image.__version__}")
    except ImportError as e:
        print(f"✗ Pillow import failed: {e}")
        return False
    
    try:
        import numpy as np
        print(f"✓ NumPy version: {np.__version__}")
    except ImportError as e:
        print(f"✗ NumPy import failed: {e}")
        return False
    
    try:
        import sqlite3
        print(f"✓ SQLite3 version: {sqlite3.sqlite_version}")
    except ImportError as e:
        print(f"✗ SQLite3 import failed: {e}")
        return False
    
    try:
        import tkinter as tk
        print("✓ Tkinter imported successfully")
    except ImportError as e:
        print(f"✗ Tkinter import failed: {e}")
        return False
    
    return True

def test_face_detection():
    """Test basic face detection functionality."""
    print("\nTesting face detection...")
    
    try:
        import cv2
        import numpy as np
        
        # Create a simple test image
        test_image = np.zeros((200, 200, 3), dtype=np.uint8)
        
        # Load face cascade
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        if face_cascade.empty():
            print("✗ Face cascade classifier failed to load")
            return False
        
        print("✓ Face cascade classifier loaded successfully")
        return True
        
    except Exception as e:
        print(f"✗ Face detection test failed: {e}")
        return False

def test_database():
    """Test database functionality."""
    print("\nTesting database...")
    
    try:
        import sqlite3
        
        # Test database creation
        conn = sqlite3.connect(":memory:")
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                data TEXT
            )
        ''')
        
        cursor.execute("INSERT INTO test_table (data) VALUES (?)", ("test",))
        conn.commit()
        
        cursor.execute("SELECT * FROM test_table")
        result = cursor.fetchone()
        
        conn.close()
        
        if result and result[1] == "test":
            print("✓ Database functionality working")
            return True
        else:
            print("✗ Database test failed")
            return False
            
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        return False

def test_application_modules():
    """Test if application modules can be imported."""
    print("\nTesting application modules...")
    
    # Add current directory to path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    modules = [
        'face_recognition_engine',
        'database_manager',
        'photo_manager',
        'config'
    ]
    
    for module in modules:
        try:
            __import__(module)
            print(f"✓ {module} imported successfully")
        except ImportError as e:
            print(f"✗ {module} import failed: {e}")
            return False
        except Exception as e:
            print(f"✗ {module} error: {e}")
            return False
    
    return True

def test_gui():
    """Test if GUI can be initialized."""
    print("\nTesting GUI initialization...")
    
    try:
        import tkinter as tk
        
        # Test basic tkinter functionality
        root = tk.Tk()
        root.withdraw()  # Hide the window
        
        # Test if we can create basic widgets
        frame = tk.Frame(root)
        label = tk.Label(frame, text="Test")
        button = tk.Button(frame, text="Test")
        
        root.destroy()
        
        print("✓ GUI components working")
        return True
        
    except Exception as e:
        print(f"✗ GUI test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Face-Based Photo Search & Management System - Installation Test")
    print("=" * 70)
    
    tests = [
        ("Import Test", test_imports),
        ("Face Detection Test", test_face_detection),
        ("Database Test", test_database),
        ("Application Modules Test", test_application_modules),
        ("GUI Test", test_gui)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 30)
        
        try:
            if test_func():
                passed += 1
                print(f"✓ {test_name} PASSED")
            else:
                print(f"✗ {test_name} FAILED")
        except Exception as e:
            print(f"✗ {test_name} FAILED with exception: {e}")
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All tests passed! The system is ready to use.")
        print("\nTo start the application, run:")
        print("python main.py")
        return 0
    else:
        print("✗ Some tests failed. Please check the requirements and installation.")
        print("\nTo install missing dependencies, run:")
        print("pip install -r requirements.txt")
        return 1

if __name__ == "__main__":
    sys.exit(main())
