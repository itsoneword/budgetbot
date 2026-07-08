import sys
import os

# Add project root to the path
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)

# Import the main function from core
from src.core import main

if __name__ == "__main__":
    main() 