"""
Structured logging setup with request IDs and JSON output.
Supports colored output for terminal (errors: red, info: blue, success: green, warning: orange).
Includes daily rotating file handlers for log persistence.
"""
import logging
from logging.handlers import TimedRotatingFileHandler
import structlog
from contextvars import ContextVar
import uuid
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from time import time

# ANSI color codes
COLORS = {
    'RED': '\033[91m',
    'BLUE': '\033[94m',
    'GREEN': '\033[92m',
    'ORANGE': '\033[93m',  # Yellow/orange
    'RESET': '\033[0m',
}

# Context variable for request ID
request_id_var: ContextVar[str] = ContextVar('request_id', default='')

# Error rate limiting - track repeated errors
_error_cache = defaultdict(lambda: {'count': 0, 'last_logged': 0, 'message': ''})
_error_throttle_seconds = 60  # Only log same error once per minute

class DailyRotatingFileHandler(TimedRotatingFileHandler):
    """
    Custom handler that creates a new log file each day with format: backend-YYYY-MM-DD.log
    Ensures newest dates appear first when sorted alphabetically (by using date in filename).
    Clears the log file on app startup for fresh logs.
    """
    def __init__(self, log_dir, backupCount=30, clear_on_startup=True, **kwargs):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.backupCount = backupCount
        self.clear_on_startup = clear_on_startup
        
        # Start with today's date
        today = datetime.now().strftime("%Y-%m-%d")
        filename = str(self.log_dir / f"backend-{today}.log")
        
        # CRITICAL: Clear the log file on startup if it exists
        if self.clear_on_startup and Path(filename).exists():
            try:
                # Truncate the file to clear it (keeps the file but empties it)
                with open(filename, 'w', encoding='utf-8'):
                    pass
            except Exception as e:
                # If we can't clear it, log a warning but continue
                import logging
                logging.warning(f"Could not clear log file {filename}: {e}")
        
        super().__init__(
            filename=filename,
            when='midnight',
            interval=1,
            backupCount=backupCount,
            encoding='utf-8',
            delay=False,
            **kwargs
        )
    
    def doRollover(self):
        """
        Override rollover to create new file with new date instead of appending suffix.
        """
        if self.stream:
            self.stream.close()
            self.stream = None
        
        # Get today's date for new file
        today = datetime.now().strftime("%Y-%m-%d")
        new_filename = str(self.log_dir / f"backend-{today}.log")
        
        # Update the baseFilename so it writes to the new file
        self.baseFilename = new_filename
        
        # Open new file
        if not self.delay:
            self.stream = self._open()

def get_request_id() -> str:
    """
    Get the current request ID or generate a new one.
    
    Returns:
        Request ID string
    """
    request_id = request_id_var.get()
    if not request_id:
        request_id = str(uuid.uuid4())
        request_id_var.set(request_id)
    return request_id

def set_request_id(request_id: str):
    """
    Set the current request ID.
    
    Args:
        request_id: Request ID string
    """
    request_id_var.set(request_id)

def add_color_level(record, event_dict):
    """
    Add color to log level based on log level and message content.
    Detects success messages (✅ or 'success' keywords) and colors them green.
    """
    log_level = event_dict.get('level', '').lower()
    message = str(event_dict.get('event', ''))
    
    # Detect success messages (✅ emoji or 'success' keyword)
    is_success = '✅' in message or 'success' in message.lower() or 'completed' in message.lower()
    
    if log_level == 'error' or log_level == 'critical':
        color = COLORS['RED']
    elif log_level == 'warning':
        color = COLORS['ORANGE']
    elif log_level == 'info' and is_success:
        color = COLORS['GREEN']
    elif log_level == 'info':
        color = COLORS['BLUE']
    else:
        color = COLORS['RESET']
    
    # Add color to the level field
    if 'level' in event_dict:
        event_dict['level'] = f"{color}{event_dict['level']}{COLORS['RESET']}"
    
    return event_dict

def colored_renderer(logger, name, event_dict):
    """
    Render log entry with clear formatting and error labels.
    Errors are prominently displayed with clear labels and spacing.
    """
    log_level = event_dict.get('level', '').lower()
    timestamp = event_dict.get('timestamp', '')
    event = event_dict.get('event', '')
    
    # Extract other fields
    other_fields = {k: v for k, v in event_dict.items() 
                   if k not in ('level', 'timestamp', 'event', 'logger')}
    
    # Build output string with clear error formatting
    if log_level in ('error', 'critical'):
        # ERROR FORMAT: Big clear label with spacing
        output = "\n" + "="*80 + "\n"
        output += f"[ERROR] {timestamp}\n" if timestamp else "[ERROR]\n"
        output += "-"*80 + "\n"
        output += f"{str(event)}\n"
        if other_fields:
            fields_str = '\n'.join(f"  {k}={v}" for k, v in other_fields.items())
            output += f"{fields_str}\n"
        output += "="*80 + "\n"
    elif log_level == 'warning':
        # WARNING FORMAT: Clear label with spacing
        output = "\n" + "-"*80 + "\n"
        output += f"[WARNING] {timestamp}\n" if timestamp else "[WARNING]\n"
        output += f"{str(event)}\n"
        if other_fields:
            fields_str = ' '.join(f"{k}={v}" for k, v in other_fields.items())
            output += f"{fields_str}\n"
        output += "-"*80 + "\n"
    else:
        # INFO/DEBUG FORMAT: Normal formatting
        parts = []
        if timestamp:
            parts.append(f"[{timestamp}]")
        parts.append(f"[{log_level.upper()}]")
        if event:
            parts.append(str(event))
        
        output = ' '.join(parts)
        
        # Add other fields if present
        if other_fields:
            fields_str = ' '.join(f"{k}={v}" for k, v in other_fields.items())
            output += f" {fields_str}"
    
    return output

class RateLimitedErrorFilter(logging.Filter):
    """
    Filter to rate-limit repeated errors and warnings.
    Groups similar errors together to reduce log spam.
    """
    def filter(self, record):
        # Always allow first occurrence
        if record.levelno < logging.WARNING:
            return True
        
        # Create a unique key for this error pattern
        # Use logger name + first 100 chars of message + level
        error_key = f"{record.name}:{record.levelname}:{str(record.getMessage())[:100]}"
        
        current_time = time()
        error_info = _error_cache[error_key]
        
        # Check if enough time has passed since last log
        time_since_last = current_time - error_info['last_logged']
        
        if time_since_last >= _error_throttle_seconds:
            # Log this error and reset counter
            if error_info['count'] > 0:
                # Log summary if there were suppressed messages
                record.msg = f"{record.msg} (suppressed {error_info['count']} similar messages in last {int(time_since_last)}s)"
            
            error_info['count'] = 0
            error_info['last_logged'] = current_time
            error_info['message'] = record.getMessage()
            return True
        else:
            # Suppress this duplicate error, but increment counter
            error_info['count'] += 1
            return False


class InfoLogFilter(logging.Filter):
    """
    Filter to suppress verbose INFO logs from APScheduler and other noisy components.
    Only allows INFO logs from critical application components.
    """
    def filter(self, record):
        # Always allow ERROR and WARNING
        if record.levelno >= logging.WARNING:
            return True
        
        # Suppress INFO logs from APScheduler (very verbose)
        if record.name.startswith('apscheduler'):
            # Only allow ERROR and WARNING from APScheduler
            return record.levelno >= logging.WARNING
        
        # Suppress INFO logs from third-party libraries that are too verbose
        noisy_loggers = [
            'urllib3',
            'httpx',
            'httpcore',
            'asyncio',
            'tensorflow',
            'transformers',
            'redis',
            'yfinance',  # Suppress yfinance INFO logs (they're very verbose)
            'absl',      # Suppress absl warnings (deprecation warnings)
        ]
        for noisy in noisy_loggers:
            if record.name.startswith(noisy):
                # For yfinance, suppress repetitive "possibly delisted" errors
                if noisy == 'yfinance' and record.levelno == logging.ERROR:
                    msg = str(record.getMessage()).lower()
                    if 'possibly delisted' in msg or 'no price data' in msg:
                        return False  # Suppress repetitive yfinance errors
                # For absl, suppress deprecation warnings
                if noisy == 'absl' and record.levelno == logging.WARNING:
                    msg = str(record.getMessage()).lower()
                    if 'deprecated' in msg or 'save_format' in msg:
                        return False  # Suppress deprecation warnings
                return record.levelno >= logging.WARNING
        
        # Suppress repetitive "No data returned" warnings from data_fetcher
        if record.name == 'backend.utils.data_fetcher' and record.levelno == logging.WARNING:
            msg = str(record.getMessage())
            if 'No data returned' in msg:
                # These are rate-limited by RateLimitedErrorFilter, but we can also suppress them here
                # They're logged too frequently and not actionable
                return False
        
        # Allow INFO logs from our application code
        # This includes backend.* modules
        if record.name.startswith('backend'):
            return True
        
        # Suppress other INFO logs by default
        return False


def configure_logging(log_level: str = "WARNING", use_colors: bool = False, log_dir: str = None):
    """
    Configure structured logging with clear error formatting.
    Errors are displayed with prominent labels and spacing for readability.
    Logs are written to both console (stdout) and daily rotating files.
    
    By default, INFO logs are suppressed to reduce verbosity. Only ERROR and WARNING
    logs are shown unless explicitly enabled for specific components.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
                  Default: WARNING to reduce log verbosity
        use_colors: Whether to use ANSI color codes (default: False for better log file readability)
        log_dir: Directory for log files (default: logs/ relative to project root)
    """
    # Determine log directory
    if log_dir is None:
        # Default to logs/ directory relative to backend directory
        backend_dir = Path(__file__).parent.parent
        log_dir = backend_dir.parent / "logs"
    else:
        log_dir = Path(log_dir)
    
    # Create log directory if it doesn't exist
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Remove existing handlers to avoid conflicts
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create filter to suppress verbose INFO logs
    info_filter = InfoLogFilter()
    
    # Create filter to rate-limit repeated errors
    rate_limit_filter = RateLimitedErrorFilter()
    
    # Setup console handler (stdout) - always keep this for real-time monitoring
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    console_handler.setLevel(getattr(logging, log_level.upper()))
    # Apply filters
    if log_level.upper() == "INFO":
        console_handler.addFilter(info_filter)
    # Always apply rate limiting for errors/warnings
    console_handler.addFilter(rate_limit_filter)
    
    # Setup daily rotating file handler with date-based filenames
    # Format: backend-YYYY-MM-DD.log (current day's file always has today's date)
    # CRITICAL: Clear the log file on startup for fresh logs
    try:
        file_handler = DailyRotatingFileHandler(
            log_dir=log_dir,
            backupCount=30,  # Keep 30 days of logs
            clear_on_startup=True  # Clear log file on app startup
        )
        
        # Get the log file path from the handler for logging
        log_file_path = file_handler.baseFilename
    except Exception as e:
        # Fallback to simple file handler if custom handler fails
        today = datetime.now().strftime("%Y-%m-%d")
        log_file_path = str(log_dir / f"backend-{today}.log")
        
        # Clear the log file if it exists
        if Path(log_file_path).exists():
            try:
                with open(log_file_path, 'w', encoding='utf-8'):
                    pass
            except Exception:
                pass
        
        file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
        root_logger.warning(f"Failed to create DailyRotatingFileHandler, using simple FileHandler: {e}")
    
    # Use a formatter that includes timestamp for file logs
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(getattr(logging, log_level.upper()))
    # Apply filters to file handler as well
    if log_level.upper() == "INFO":
        file_handler.addFilter(info_filter)
    # Always apply rate limiting for errors/warnings
    file_handler.addFilter(rate_limit_filter)
    
    # Ensure the file handler is opened (TimedRotatingFileHandler opens it if delay=False)
    # But we need to make sure it's actually writing
    if not file_handler.stream:
        try:
            file_handler.stream = file_handler._open()
        except AttributeError:
            # Some handlers don't have _open, they open automatically
            pass
    
    # Configure root logger with both handlers
    root_logger.setLevel(getattr(logging, log_level.upper()))
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Fix APScheduler logger - set to WARNING to suppress INFO logs
    apscheduler_logger = logging.getLogger('apscheduler')
    for handler in apscheduler_logger.handlers[:]:
        apscheduler_logger.removeHandler(handler)
    apscheduler_logger.addHandler(console_handler)
    apscheduler_logger.addHandler(file_handler)
    # Set APScheduler to WARNING level to suppress "executed successfully" INFO messages
    apscheduler_logger.setLevel(logging.WARNING)
    
    # Also suppress INFO logs from APScheduler executors
    apscheduler_executor_logger = logging.getLogger('apscheduler.executors.default')
    apscheduler_executor_logger.setLevel(logging.WARNING)
    
    # Configure structlog with clear renderer
    # Use colored renderer only if colors are enabled
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        colored_renderer,  # Always use clear renderer (colors disabled by default)
    ]
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Log the configuration and startup message
    # Always log startup messages regardless of log level
    startup_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    root_logger.info(f"📝 Log file cleared and ready for new session: {log_file_path}")
    root_logger.info(f"🚀 Application started at {startup_time}")
    
    # Log configuration details (only if not INFO level to avoid redundancy)
    if log_level.upper() != "INFO":
        root_logger.warning(f"Logging configured: level={log_level.upper()}, log_file={log_file_path}, backup_count=30 days")

def get_logger(name: str = None):
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Structlog logger instance
    """
    return structlog.get_logger(name)

