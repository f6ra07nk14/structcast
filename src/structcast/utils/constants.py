"""Constants for StructCast utilities."""

DEFAULT_ALLOWED_MODULES: set[str] = {
    # --- Core Data Structures ---
    "collections",
    "datetime",
    "uuid",
    "decimal",
    "enum",
    # --- Logic & Math ---
    "math",
    "itertools",
    "functools",
    "random",
    "secrets",
    # --- Text & Encoding ---
    "string",
    "base64",
    "json",
    "html",
    # --- Parsing (Network safe) ---
    "urllib.parse",
    "ipaddress",
    # --- Project Self-Ref ---
    "structcast",
}

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
    "urllib.request",  # URL handling modules
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

# Security: Only strictly safe builtins are allowed
DEFAULT_ALLOWED_BUILTINS = {
    # --- Data Types (Constructors) ---
    "bool",
    "int",
    "float",
    "complex",
    "str",
    "bytes",
    "bytearray",
    "list",
    "tuple",
    "set",
    "frozenset",
    "dict",
    # --- Inspection / Helpers (Safe) ---
    "len",  # Get length
    "abs",  # Absolute value
    "min",
    "max",  # Min/Max value
    "sum",  # Summation
    "all",
    "any",  # Boolean logic
    "divmod",  # Division
    "round",  # Rounding
    "hash",  # Hashing (safe for immutable types)
    "id",  # Object ID (mostly harmless, though sometimes leaks info)
    "enumerate",  # Loop helper
    "zip",  # Loop helper
    "range",  # Loop helper
    "reversed",  # Loop helper
    "sorted",  # Sorting
    "filter",  # Functional helper
    "map",  # Functional helper
    "pow",  # Power function
    "slice",  # Slice object
    # --- Formatting ---
    "format",  # String formatting
    "chr",  # Int to Char
    "ord",  # Char to Int
    "bin",
    "oct",
    "hex",  # Number formatting
    "ascii",  # ASCII representation
    "repr",  # String representation (Usually safe, but watch out for massive outputs)
    # --- Errors ---
    # Allowing Exception types is usually fine for raising errors
    "Exception",
    "ValueError",
    "TypeError",
    "KeyError",
    "IndexError",
}

# Security: Dangerous dunder methods that should be blocked by default
DEFAULT_DANGEROUS_DUNDERS = {
    "__subclasses__",
    "__bases__",
    "__globals__",
    "__code__",
    "__dict__",
    "__class__",
    "__mro__",
    "__init__",
    "__import__",
}
