import logging
import inspect
import os
import time
import functools
import sys
from logging.handlers import TimedRotatingFileHandler

# Global settings
class LogConfig:
    """Central configuration for all logging functionality"""
    DEBUG_MODE = False
    LOG_LEVELS = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    
    # Log directories and files
    LOG_DIR = "user_data"
    APP_LOG_FILE = "app.log"
    USER_LOG_FILE = "global_log.txt"
    
    # Log formats
    STANDARD_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
    DEBUG_FORMAT = "%(levelname)s: %(message)s"
    USER_FORMAT = "%(asctime)s - %(message)s"
    
    # Filter settings
    FILTERED_PATTERNS = [
        'connect_tcp', 
        'start_tls', 
        'send_request', 
        'receive_response',
        'looking for jobs',
        'Bot API',
        'getUpdates',
        'Calling Bot API',
        'No jobs; waiting',
        'findfont:',
        'font_manager',
        'Matching '
    ]

# Ensure log directory exists
os.makedirs(LogConfig.LOG_DIR, exist_ok=True)

# Custom logging filter to exclude certain debug messages
class DebugFilter(logging.Filter):
    """Filter to exclude noisy debug messages"""
    def filter(self, record):
        if record.levelno == logging.DEBUG:
            msg = record.getMessage()
            for pattern in LogConfig.FILTERED_PATTERNS:
                if pattern.lower() in msg.lower():
                    return False
        return True

# Create loggers
root_logger = logging.getLogger()
user_logger = logging.getLogger("user_interactions")
user_logger.propagate = False  # Don't propagate to root logger

def setup_logging(debug_level="INFO"):
    """Set up the logging system with the specified debug level
    
    Args:
        debug_level: String level name ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
                    or boolean (True for DEBUG, False for WARNING)
    """
    # Convert boolean to string level
    if isinstance(debug_level, bool):
        debug_level = "DEBUG" if debug_level else "WARNING"
    
    # Get the numeric level
    level = LogConfig.LOG_LEVELS.get(debug_level.upper(), logging.INFO)
    
    # Update the global debug mode flag
    LogConfig.DEBUG_MODE = (level <= logging.DEBUG)
    
    # Clear any existing handlers from the root logger
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Clear any existing handlers from the user logger
    for handler in user_logger.handlers[:]:
        user_logger.removeHandler(handler)
    
    # === Configure root logger ===
    
    # Set up file handler for application logging
    app_log_path = os.path.join(LogConfig.LOG_DIR, LogConfig.APP_LOG_FILE)
    file_handler = TimedRotatingFileHandler(
        app_log_path,
        when="m",
        interval=10,
        backupCount=5
    )
    
    # Set the file handler level - use DEBUG level if in debug mode
    file_handler.setLevel(logging.DEBUG if LogConfig.DEBUG_MODE else logging.INFO)
    file_formatter = logging.Formatter(LogConfig.STANDARD_FORMAT)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    if LogConfig.DEBUG_MODE:
        console_handler.setLevel(logging.DEBUG)
        root_logger.setLevel(logging.DEBUG)
        console_formatter = logging.Formatter(LogConfig.DEBUG_FORMAT)
        logging.info("Debug mode is ON - verbose logging enabled")
        
        # Add filter to console handler
        console_handler.addFilter(DebugFilter())
    else:
        console_handler.setLevel(logging.WARNING)
        root_logger.setLevel(logging.INFO)
        console_formatter = logging.Formatter(LogConfig.STANDARD_FORMAT)
    
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # === Configure user interaction logger ===
    user_log_path = os.path.join(LogConfig.LOG_DIR, LogConfig.USER_LOG_FILE)
    user_handler = logging.FileHandler(user_log_path)
    user_handler.setLevel(logging.INFO)
    user_formatter = logging.Formatter(LogConfig.USER_FORMAT)
    user_handler.setFormatter(user_formatter)
    user_logger.addHandler(user_handler)
    
    # === Configure external loggers to reduce noise ===
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.INFO)
    logging.getLogger("telegram.ext").setLevel(logging.INFO)
    logging.getLogger("JobQueue").setLevel(logging.INFO)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    # Configure Matplotlib logging
    logging.getLogger("matplotlib.font_manager").setLevel(logging.INFO)
    logging.getLogger("matplotlib.backends").setLevel(logging.INFO)
    logging.getLogger("matplotlib").setLevel(logging.INFO)
    
    # Return the current debug status
    return LogConfig.DEBUG_MODE

def set_log_level(level):
    """Update the logging level
    
    Args:
        level: String level name ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
              or boolean (True for DEBUG, False for WARNING)
    """
    return setup_logging(level)

# === Core logging functions ===

def log_debug(message, function_name=None, execution_time=None):
    """Log debug information when debug mode is enabled
    
    Args:
        message: The debug message to log
        function_name: Optional function name (auto-detected if not provided)
        execution_time: Optional execution time to include in message
    """
    if not LogConfig.DEBUG_MODE:
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
    """Log only the function name when it's called
    
    Args:
        function_name: Optional function name (auto-detected if not provided)
    """
    if not LogConfig.DEBUG_MODE:
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
    """Log state machine transitions
    
    Args:
        state_name: The name of the new state
    """
    if not LogConfig.DEBUG_MODE:
        return
        
    # Get the calling function's name
    stack = inspect.stack()
    if len(stack) > 1:
        function_name = stack[1].function
    else:
        function_name = "unknown"
        
    logging.debug(f"STATE TRANSITION: {function_name} → {state_name}")

def log_user_interaction(user_id, username, tg_username, function_name=None):
    """Log user interactions to the user log file
    
    Args:
        user_id: User ID
        username: User's name
        tg_username: Telegram username
        function_name: Optional function name (auto-detected if not provided)
    """
    calling_function_name = function_name if function_name else inspect.stack()[1].function
    log_message = f"UserID: {user_id}, {username}, {tg_username}, {calling_function_name}"
    user_logger.info(log_message)

# === Function decorators and measurement tools ===

def timed_function(func=None, log_args=False):
    """Decorator to automatically time and log function execution
    
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
            if not LogConfig.DEBUG_MODE:
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
    """Context manager for measuring execution time of a code block
    
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
            if LogConfig.DEBUG_MODE:
                execution_time = time.time() - self.start_time
                
                # Get the calling function's name
                frame = inspect.currentframe().f_back
                function_name = frame.f_code.co_name
                
                if self.message:
                    log_debug(f"Completed: {self.message}", function_name, execution_time)
                else:
                    log_debug("Code block completed", function_name, execution_time)
    
    return ExecutionTimer(message)

# === Legacy functions for backward compatibility ===

def start_function_log(message=None):
    """Legacy function - maintained for backward compatibility"""
    log_function_call()
    return time.time()

def end_function_log(start_time, message=None):
    """Legacy function - maintained for backward compatibility"""
    if not LogConfig.DEBUG_MODE:
        return
    
    execution_time = time.time() - start_time
    
    # Get the calling function's name
    frame = inspect.currentframe().f_back
    function_name = frame.f_code.co_name
    
    # Only log the completion time, not the detailed message
    log_debug("Completed", function_name, execution_time)

# === Helper functions to configure logger from config file ===

def load_debug_setting_from_config(config):
    """Load debug setting from config file
    
    Args:
        config: ConfigParser object with loaded configuration
        
    Returns:
        Boolean indicating whether debug is enabled
    """
    try:
        if config.has_section("DEBUG") and config.has_option("DEBUG", "ENABLED"):
            debug_mode = config.getboolean("DEBUG", "ENABLED")
            return debug_mode
    except Exception as e:
        logging.warning(f"Error reading debug configuration: {e}")
    return False

def save_debug_setting_to_config(config, debug_mode, config_file="configs/config"):
    """Save debug setting to config file
    
    Args:
        config: ConfigParser object to update
        debug_mode: Boolean indicating whether debug should be enabled
        config_file: Path to the config file
        
    Returns:
        Boolean indicating success
    """
    try:
        if not config.has_section("DEBUG"):
            config.add_section("DEBUG")
        
        config.set("DEBUG", "ENABLED", str(debug_mode))
        
        with open(config_file, "w") as configfile:
            config.write(configfile)
        
        return True
    except Exception as e:
        logging.error(f"Error saving debug configuration: {e}")
        return False 