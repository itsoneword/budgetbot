import logging
import inspect
import os
import time
import functools

# Global debug mode flag (will be synchronized with core.py)
DEBUG_MODE = False

# We'll use the root logger instead of a separate debug logger
# The root logger's configuration will be handled in core.py

def log_debug(message, function_name=None, execution_time=None):
    """Log debug information when debug mode is enabled
    
    This can be imported by any module to provide consistent debug logging.
    """
    if not DEBUG_MODE:
        return
        
    if not function_name:
        # Get the calling function's name if not provided
        stack = inspect.stack()
        # Use the caller's caller if available (to skip the log_debug function itself)
        if len(stack) > 2:
            function_name = stack[1].function
        else:
            function_name = "unknown"
    
    # Format the message with execution time if provided
    if execution_time is not None:
        formatted_message = f"[{execution_time:.2f}s] {message}"
    else:
        formatted_message = message
            
    logging.debug(f"{function_name}: {formatted_message}")

def log_function_call(function_name=None):
    """Log only the function name when it's called.
    
    This is a lightweight alternative to start_function_log/end_function_log
    for tracking just function entry points.
    """
    if not DEBUG_MODE:
        return
        
    if not function_name:
        # Get the calling function's name if not provided
        stack = inspect.stack()
        if len(stack) > 1:
            function_name = stack[1].function
        else:
            function_name = "unknown"
            
    logging.debug(f"CALLED: {function_name}")

def log_state_transition(state_name):
    """Log state machine transitions.
    
    Use this when returning a state in the conversation handler.
    """
    if not DEBUG_MODE:
        return
        
    # Get the calling function's name
    stack = inspect.stack()
    if len(stack) > 1:
        function_name = stack[1].function
    else:
        function_name = "unknown"
        
    logging.debug(f"STATE TRANSITION: {function_name} → {state_name}")

def timed_function(func=None, log_args=False):
    """Decorator to automatically time and log function execution.
    
    Usage:
        @timed_function
        def my_function(arg1, arg2):
            # function code
            
        @timed_function(log_args=True)
        def my_function(arg1, arg2):
            # function code
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if not DEBUG_MODE:
                return fn(*args, **kwargs)
                
            start_time = time.time()
            
            # Log function start with arguments if requested
            if log_args:
                args_str = ', '.join([str(arg) for arg in args])
                kwargs_str = ', '.join([f"{k}={v}" for k, v in kwargs.items()])
                params = f"{args_str}{', ' if args_str and kwargs_str else ''}{kwargs_str}"
                log_debug(f"Started with args: {params}", fn.__name__)
            else:
                log_debug(f"CALLED", fn.__name__)
            
            # Execute the function
            result = fn(*args, **kwargs)
            
            # Log function completion with timing
            execution_time = time.time() - start_time
            log_debug("Completed", fn.__name__, execution_time)
            
            return result
        return wrapper
        
    # Handle both @timed_function and @timed_function(log_args=True) syntax
    if func is None:
        return decorator
    return decorator(func)

def measure_execution(message=None):
    """Context manager for measuring execution time of a code block.
    
    Usage:
        with measure_execution("Database query"):
            # code to measure
    """
    class ExecutionTimer:
        def __init__(self, message):
            self.message = message
            self.start_time = None
            
        def __enter__(self):
            self.start_time = time.time()
            return self
            
        def __exit__(self, exc_type, exc_val, exc_tb):
            if DEBUG_MODE:
                execution_time = time.time() - self.start_time
                
                # Get the calling function's name
                frame = inspect.currentframe().f_back
                function_name = frame.f_code.co_name
                
                if self.message:
                    log_debug(f"Completed: {self.message}", function_name, execution_time)
                else:
                    log_debug("Code block completed", function_name, execution_time)
    
    return ExecutionTimer(message)

# Legacy functions - maintained for backward compatibility
# but simplified to call the new streamlined functions
def start_function_log(message=None):
    log_function_call()
    return time.time()

def end_function_log(start_time, message=None):
    if not DEBUG_MODE:
        return
    
    execution_time = time.time() - start_time
    
    # Get the calling function's name
    frame = inspect.currentframe().f_back
    function_name = frame.f_code.co_name
    
    # Only log the completion time, not the detailed message
    log_debug("Completed", function_name, execution_time)

def set_debug_mode(enabled):
    """Update debug mode across all modules using this utility"""
    global DEBUG_MODE
    DEBUG_MODE = enabled
    
    # Configure the logger level based on debug mode
    root_logger = logging.getLogger()
    
    # Check the console handlers and update their level
    for handler in root_logger.handlers:
        if isinstance(handler, logging.StreamHandler):
            if DEBUG_MODE:
                handler.setLevel(logging.DEBUG)
            else:
                handler.setLevel(logging.WARNING)
                
    # Log the debug mode change
    status = "ON" if enabled else "OFF"
    if enabled:
        logging.debug(f"set_debug_mode: Debug mode is now {status}")
    
    return enabled 