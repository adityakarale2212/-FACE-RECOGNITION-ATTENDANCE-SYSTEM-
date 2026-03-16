import sys
import os

print(f"Python Executable: {sys.executable}")
print(f"Python Version: {sys.version}")
print("\n--- Search Paths ---")
for p in sys.path:
    print(p)

print("\n--- Attempting Imports ---")
try:
    import face_recognition_models
    print(f"SUCCESS: face_recognition_models imported from {face_recognition_models.__file__}")
except ImportError as e:
    print(f"FAILED: face_recognition_models: {e}")

try:
    import face_recognition
    print("SUCCESS: face_recognition imported")
except Exception as e:
    print(f"FAILED: face_recognition: {e}")
