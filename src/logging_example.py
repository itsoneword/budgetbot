# Example file showing how to use the new logging utilities
# Import the utilities from debug_utils
from src.debug_utils import (
    log_debug,
    start_function_log,
    end_function_log,
    timed_function,
    measure_execution,
    set_debug_mode
)
import time

# Set debug mode to True to see the logs
set_debug_mode(True)

# Example 1: Simple logging with log_debug
def basic_log_example():
    log_debug("This is a simple log message")
    log_debug("This log includes execution time", execution_time=0.5)

# Example 2: Using start_function_log and end_function_log
def manual_timing_example():
    # Start timing and log the start
    start_time = start_function_log("Starting the process")
    
    # Do some work
    time.sleep(0.2)
    
    # Log an intermediate step
    log_debug("Processing data...")
    
    # Do more work
    time.sleep(0.3)
    
    # End timing and log the end with execution time
    end_function_log(start_time, "Process completed")

# Example 3: Using the timed_function decorator
@timed_function
def automatic_timing_example():
    # The function is automatically timed
    log_debug("Working inside a timed function")
    time.sleep(0.5)
    return "Result"

# Example 4: Using the timed_function decorator with argument logging
@timed_function(log_args=True)
def function_with_args(arg1, arg2, keyword_arg="default"):
    # Arguments will be logged automatically
    time.sleep(0.2)
    return f"{arg1} + {arg2} + {keyword_arg}"

# Example 5: Using the measure_execution context manager
def context_manager_example():
    # Simple code
    time.sleep(0.1)
    
    # Measure a specific block
    with measure_execution("Database query"):
        time.sleep(0.3)
    
    # Another block
    with measure_execution("API call"):
        time.sleep(0.2)
    
    # Nested measurements
    with measure_execution("Outer operation"):
        time.sleep(0.1)
        with measure_execution("Inner operation"):
            time.sleep(0.2)

if __name__ == "__main__":
    print("Running logging examples...")
    
    basic_log_example()
    manual_timing_example()
    automatic_timing_example()
    function_with_args("hello", "world", keyword_arg="custom")
    context_manager_example()
    
    print("All examples completed. Check the logs!") 