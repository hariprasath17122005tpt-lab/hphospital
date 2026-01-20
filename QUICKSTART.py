#!/usr/bin/env python
"""
QUICK START: Medical AI Chatbot
Run this to get started immediately
"""

import os
import subprocess
import sys

def run_command(cmd, description):
    """Run a command and show progress"""
    print(f"\n{'='*60}")
    print(f"⏳ {description}")
    print(f"{'='*60}")
    print(f"Command: {cmd}\n")
    
    result = os.system(cmd)
    
    if result != 0:
        print(f"\n⚠️  Command failed. Continue? (y/n): ", end="")
        if input().lower() != 'y':
            return False
    
    return True

def main():
    print(f"\n{'='*60}")
    print("🧠 MEDICAL AI CHATBOT - QUICK START")
    print(f"{'='*60}")
    
    steps = [
        ("Dataset already prepared ✓", None),
        ("Step 1: Fine-Tune Model (THIS IS CRITICAL)", 
         "python train.py"),
        ("Step 2: Test Chatbot", 
         "python chat.py"),
    ]
    
    for i, (description, cmd) in enumerate(steps, 1):
        if cmd is None:
            print(f"\n✅ {description}")
            continue
        
        if not run_command(cmd, f"Step {i}: {description}"):
            print("Setup incomplete!")
            return 1
    
    print(f"\n{'='*60}")
    print("✅ SETUP COMPLETE!")
    print(f"{'='*60}")
    print("""
Next:
1. Start Flask server:
   python run_server.py
   
2. Open browser:
   http://localhost:5000
   
3. Go to Symptom Checker
4. Chat with the AI!
""")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
