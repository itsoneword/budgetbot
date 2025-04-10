# Logger Module

This module provides a centralized logging system for the BudgetBot application.

## Features

- Unified logging configuration for all parts of the application
- Multiple log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Separate logs for application events and user interactions
- Timed function execution tracking
- State transition logging
- Code block execution time measurement
- Filter for noisy debug messages

## Log Files

- **Application logs**: `user_data/app.log`
- **User interaction logs**: `user_data/global_log.txt`

## Usage

### Basic Setup

```python
from src.logger import setup_logging

# Initialize logging with default settings (INFO level)
setup_logging()

# Or specify a level
setup_logging("DEBUG")  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### Debug Logging

```python
from src.logger import log_debug

# Simple debug message
log_debug("Operation completed")

# With execution time
log_debug("Database query completed", execution_time=0.35)

# With custom function name
log_debug("Processing data", function_name="custom_processor")
```

### Function Tracking

```python
from src.logger import log_function_call, timed_function

# Manual function call logging
def my_function():
    log_function_call()  # Logs that the function was called
    # Function code...

# Automatic timing with decorator
@timed_function
def another_function():
    # This function will log when it starts and completes with timing
    pass

# Log arguments as well
@timed_function(log_args=True)
def function_with_args(arg1, arg2):
    # This will log the function arguments as well
    pass
```

### Measuring Code Blocks

```python
from src.logger import measure_execution

def complex_function():
    # Regular code
    
    # Measure a specific block
    with measure_execution("Database query"):
        # This block will be timed
        pass
```

### State Transitions

```python
from src.logger import log_state_transition

def state_handler():
    # Handle state
    # ...
    
    # Log transition to next state
    log_state_transition("NEXT_STATE")
    return NEXT_STATE
```

### User Interaction Logging

```python
from src.logger import log_user_interaction

def handle_command(update, context):
    user_id = update.effective_user.id
    username = update.effective_user.first_name
    tg_username = update.effective_user.username
    
    log_user_interaction(user_id, username, tg_username)
    # Rest of the handler...
```

## Configuration

You can customize the logging system by modifying the `LogConfig` class in `logger.py`:

```python
class LogConfig:
    # Debug mode flag
    DEBUG_MODE = False
    
    # Log levels mapping
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
    
    # Filter settings - patterns to exclude from debug logs
    FILTERED_PATTERNS = [
        'connect_tcp', 
        'start_tls',
        # Add more patterns here
    ]
```

## Integration with Config File

The logger module includes functions to read/write debug settings from/to the application config file:

```python
from src.logger import load_debug_setting_from_config, save_debug_setting_to_config
import configparser

# Load config file
config = configparser.ConfigParser()
config.read("configs/config")

# Read debug setting
debug_mode = load_debug_setting_from_config(config)

# Save debug setting
save_debug_setting_to_config(config, True)
```

## Example

See `src/logging_example.py` for a complete example of how to use all the logging features. 