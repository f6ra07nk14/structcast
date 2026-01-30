"""Constants for StructCast utilities."""

DEFAULT_ALLOWED_MODULES: set[str] = {"builtins", "structcast"}

# Security: Dangerous modules that should be blocked by default
DEFAULT_BLOCKED_MODULES = {
    # --- System & Process Management ---
    "os",  # Operating system interfaces (file system, process management)
    "subprocess",  # Spawning new processes
    "sys",  # System-specific parameters and functions (manipulate runtime)
    "shutil",  # High-level file operations (copy, move, delete trees)
    "platform",  # Access to underlying platform data
    "commands",  # Legacy system command execution (deprecated but dangerous)
    "posix",  # POSIX standard functions (low-level OS access)
    "nt",  # Windows specific low-level OS access
    # --- Code Execution & Import Machinery ---
    "importlib",  # Advanced import machinery
    "runpy",  # Locating and executing Python modules
    "pkgutil",  # Package extension utility
    "imp",  # Legacy import machinery
    "code",  # Facilities to implement read-eval-print loops
    "codeop",  # Compile Python code
    # --- Low-Level / C-Interface (CRITICAL RISKS) ---
    "ctypes",  # Foreign Function Interface (can load C libs to bypass Python sandbox)
    "cffi",  # C Foreign Function Interface
    "mmap",  # Memory-mapped file support (direct memory access)
    # --- Serialization (RCE Risks) ---
    "pickle",  # Python object serialization (arbitrary code execution risk)
    "shelve",  # Python object persistence (uses pickle)
    "marshal",  # Internal Python object serialization
    "dill",  # Extended pickle module (often used in data science)
    "dbm",  # Interface to Unix "database" files
    # --- Network (SSRF & Data Exfiltration Risks) ---
    "socket",  # Low-level networking interface
    "ssl",  # TLS/SSL wrapper for socket objects
    "asyncio",  # Asynchronous I/O (often involves networking)
    "requests",  # HTTP library (if installed, commonly targeted for SSRF)
    "urllib",  # URL handling modules
    "http",  # HTTP protocol clients
    "ftplib",  # FTP protocol client
    "poplib",  # POP3 protocol client
    "imaplib",  # IMAP4 protocol client
    "smtplib",  # SMTP protocol client
    "telnetlib",  # Telnet client
    "xmlrpc",  # XML-RPC client
    # --- File System (Beyond 'os') ---
    "pathlib",  # Object-oriented filesystem paths (can read/write files)
    "glob",  # Unix style pathname pattern expansion
    "tempfile",  # Generate temporary files and directories
    "fileinput",  # Iterate over lines from multiple input streams
    "io",  # Core tools for working with streams
    # --- Introspection & Debugging ---
    "inspect",  # Inspect live objects (can retrieve source code or stack frames)
    "pdb",  # The Python Debugger (interactive shell risk)
    "traceback",  # Print or retrieve a stack traceback
    "faulthandler",  # Dump the Python traceback
    "gc",  # Garbage Collector interface
    "pty",  # Pseudo-terminal utilities
    # --- Threading & Concurrency (DoS Risks) ---
    "threading",  # Thread-based parallelism
    "multiprocessing",  # Process-based parallelism
    "concurrent",  # Launching parallel tasks
}

# Security: Dangerous builtins that should be blocked by default
DEFAULT_BLOCKED_BUILTINS = {
    # --- Execution & Compilation ---
    "eval",  # Evaluate Python expressions
    "exec",  # Execute dynamic Python code
    "compile",  # Compile source into code objects
    "__import__",  # Core import function (primary target for bypasses)
    # --- File & I/O ---
    "open",  # Open files (read/write access)
    "input",  # Read string from standard input (blocks execution)
    "print",  # Writing to stdout (can be used for spamming/DoS in some contexts)
    # --- System & Lifecycle ---
    "exit",  # Exit the interpreter
    "quit",  # Alias for exit
    "help",  # Invokes the built-in help system (can be interactive)
    "breakpoint",  # Drops into the debugger
    # --- Introspection & Attribute Access ---
    # Blocking these prevents attackers from traversing the object graph
    # to find hidden modules (gadget chains).
    "globals",  # Access to the global symbol table
    "locals",  # Access to the local symbol table
    "vars",  # Return __dict__ attribute
    "dir",  # Return list of attributes
    "getattr",  # Get attribute value (critical for gadget chains)
    "setattr",  # Set attribute value (can corrupt internal state)
    "delattr",  # Delete attribute
    "hasattr",  # Check for attribute existence
    # --- Low-level Types ---
    "memoryview",  # Direct access to internal data of an object
    "staticmethod",  # Often used in gadget chains
    "classmethod",  # Often used in gadget chains
    "type",  # Can be used to create new classes dynamically
}
