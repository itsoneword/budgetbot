import sys
import os

# Add the src directory to the path so we can import modules from it
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

# Import the main function from core
from core import main

if __name__ == "__main__":
    main() 