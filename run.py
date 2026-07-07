import sys
import os

# Add project root and src directory to the path
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'src'))

# Import the main function from core
from core import main

if __name__ == "__main__":
    main() 