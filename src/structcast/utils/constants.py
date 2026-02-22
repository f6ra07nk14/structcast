"""Constants for StructCast utilities."""

from typing import Optional

import structcast.utils.security

DEFAULT_DANGEROUS_DUNDERS: set[str] = {
    *{"__subclasses__", "__bases__", "__globals__", "__code__", "__dict__"},
    *{"__class__", "__mro__", "__init__", "__import__"},
}
"""Default dangerous dunder attributes to block during instantiation."""

DEFAULT_ALLOWED_DUNDERS: set[str] = {
    *{"__annotations__", "__doc__", "__name__", "__file__", "__path__", "__version__"},
    *{"__all__", "__spec__", "__loader__", "__package__"},
}

DEFAULT_BLOCKED_MODULES: set[str] = {
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
    # --- Protecting Self-Import ---
    "structcast.utils",  # Prevent self-import to avoid security bypass
}
"""Default blocked modules for StructCast instantiation."""


DEFAULT_ALLOWED_MODULES: dict[str, Optional[set[Optional[str]]]] = {
    # --- Core Data Structures ---
    "builtins": {
        # --- Data Types (Constructors) ---
        *{"bool", "int", "float", "complex", "str", "bytes", "bytearray", "list", "tuple", "set", "frozenset", "dict"},
        # --- Inspection / Helpers (Safe) ---
        *{"len", "abs", "min", "max", "sum", "all", "any", "zip", "map", "pow", "hash", "id"},
        *{"divmod", "round", "enumerate", "range", "reversed", "sorted", "filter", "slice"},
        # --- Formatting ---
        *{"format", "chr", "ord", "bin", "oct", "hex", "ascii", "repr"},
        # --- Errors ---
        *{"Exception", "ValueError", "TypeError", "KeyError", "IndexError"},
    },
    "collections": {
        *{"ChainMap", "Counter", "OrderedDict", "UserDict", "UserList"},
        *{"UserString", "defaultdict", "deque", "namedtuple"},
    },
    "datetime": {"date", "datetime", "time", "timedelta", "timezone", "tzinfo", "MINYEAR", "MAXYEAR"},
    "time": {
        *{"altzone", "daylight", "timezone", "tzname", "CLOCK_BOOTTIME", "CLOCK_PROF", "CLOCK_UPTIME"},
        *{"CLOCK_MONOTONIC", "CLOCK_MONOTONIC_RAW", "CLOCK_PROCESS_CPUTIME_ID", "CLOCK_REALTIME"},
        *{"CLOCK_THREAD_CPUTIME_ID", "CLOCK_HIGHRES", "CLOCK_UPTIME_RAW", "CLOCK_UPTIME_RAW_APPROX"},
        *{"CLOCK_MONOTONIC_RAW_APPROX", "CLOCK_TAI", "struct_time", "asctime", "ctime", "gmtime", "localtime"},
        *{"mktime", "strftime", "time", "get_clock_info", "monotonic", "perf_counter", "process_time"},
        *{"clock_getres", "clock_gettime", "clock_gettime_ns", "pthread_getcpuclockid", "monotonic_ns"},
        *{"perf_counter_ns", "process_time_ns", "time_ns", "thread_time", "thread_time_ns"},
    },
    "uuid": {
        *{"RESERVED_NCS", "RFC_4122", "RESERVED_MICROSOFT", "RESERVED_FUTURE"},
        *{"SafeUUID", "UUID", "uuid4", "uuid1", "uuid3", "uuid5"},
        *{"NAMESPACE_DNS", "NAMESPACE_URL", "NAMESPACE_OID", "NAMESPACE_X500"},
    },
    "decimal": {
        *{"Clamped", "Context", "ConversionSyntax", "Decimal", "DecimalException", "DecimalTuple"},
        *{"DivisionByZero", "DivisionImpossible", "DivisionUndefined", "FloatOperation", "Inexact"},
        *{"InvalidContext", "InvalidOperation", "Overflow", "Rounded", "Subnormal", "Underflow"},
        *{"ROUND_DOWN", "ROUND_HALF_UP", "ROUND_HALF_EVEN", "ROUND_CEILING", "ROUND_FLOOR", "ROUND_UP"},
        *{"ROUND_HALF_DOWN", "ROUND_05UP"},
        *{"HAVE_CONTEXTVAR", "HAVE_THREADS", "MAX_EMAX", "MAX_PREC", "MIN_EMIN", "MIN_ETINY"},
        *{"getcontext", "localcontext", "DefaultContext", "BasicContext", "ExtendedContext"},
    },
    "enum": {"EnumMeta", "Enum", "IntEnum", "Flag", "IntFlag", "auto", "unique"},
    # --- Logic & Math ---
    "math": {
        *{"e", "pi", "inf", "nan", "tau"},
        *{"acos", "acosh", "asin", "asinh", "atan", "atan2", "atanh", "cbrt", "ceil", "comb", "copysign"},
        *{"cos", "cosh", "degrees", "dist", "erf", "erfc", "exp", "exp2", "expm1", "fabs", "factorial", "floor"},
        *{"fmod", "frexp", "fsum", "gamma", "gcd", "hypot", "isclose", "isfinite", "isinf", "isnan", "isqrt"},
        *{"lcm", "ldexp", "lgamma", "log", "log10", "log1p", "log2", "modf", "nextafter", "perm", "pow", "prod"},
        *{"radians", "remainder", "sin", "sinh", "sqrt", "tan", "tanh", "trunc", "ulp", "fma"},
    },
    "itertools": {
        *{"count", "cycle", "repeat", "accumulate", "chain", "compress", "dropwhile", "filterfalse"},
        *{"groupby", "islice", "starmap", "takewhile", "tee", "zip_longest", "product", "permutations", "combinations"},
        *{"combinations_with_replacement", "pairwise", "batched"},
    },
    "functools": {
        *{"update_wrapper", "wraps", "WRAPPER_ASSIGNMENTS", "WRAPPER_UPDATES", "total_ordering", "cache"},
        *{"cmp_to_key", "lru_cache", "reduce", "partial", "partialmethod", "singledispatch"},
        *{"singledispatchmethod", "cached_property"},
    },
    "random": {
        *{"Random", "SystemRandom", "betavariate", "choice", "choices", "expovariate", "gammavariate", "gauss"},
        *{"getrandbits", "getstate", "lognormvariate", "normalvariate", "paretovariate", "randbytes", "randint"},
        *{"random", "randrange", "sample", "seed", "shuffle", "triangular", "uniform"},
        *{"vonmisesvariate", "weibullvariate"},
    },
    "secrets": {
        *{"choice", "randbelow", "randbits", "SystemRandom", "token_bytes", "token_hex"},
        *{"token_urlsafe", "compare_digest"},
    },
    "operator": {
        *{"abs", "add", "and_", "concat", "contains", "countOf", "eq", "floordiv", "ge", "getitem", "gt", "index"},
        *{"indexOf", "inv", "invert", "is_", "is_not", "itemgetter", "le", "length_hint", "lshift", "lt", "matmul"},
        *{"methodcaller", "mod", "mul", "ne", "neg", "not_", "or_", "pos", "pow", "rshift"},
        *{"sub", "truediv", "truth", "xor"},
    },
    # --- Text & Encoding ---
    "string": {
        *{"ascii_letters", "ascii_lowercase", "ascii_uppercase", "capwords", "digits", "hexdigits"},
        *{"octdigits", "printable", "punctuation", "whitespace", "Formatter", "Template"},
    },
    "base64": {
        *{"encode", "decode", "encodebytes", "decodebytes", "b64encode", "b64decode", "b32encode", "b32decode"},
        *{"b16encode", "b16decode", "b85encode", "b85decode", "a85encode", "a85decode"},
        *{"standard_b64encode", "standard_b64decode", "urlsafe_b64encode", "urlsafe_b64decode"},
    },
    "json": {"dumps", "load", "loads", "JSONDecoder", "JSONDecodeError", "JSONEncoder"},
    "html": {"escape", "unescape"},
    # --- Parsing (Network safe) ---
    "urllib.parse": {
        *{"urlparse", "urlunparse", "urljoin", "urldefrag", "urlsplit", "urlunsplit", "urlencode", "parse_qs"},
        *{"parse_qsl", "quote", "quote_plus", "quote_from_bytes", "unquote", "unquote_plus", "unquote_to_bytes"},
        *{"DefragResult", "ParseResult", "SplitResult", "DefragResultBytes", "ParseResultBytes", "SplitResultBytes"},
    },
    "ipaddress": {
        *{"IPV4LENGTH", "IPV6LENGTH", "AddressValueError", "NetmaskValueError"},
        *{"ip_address", "ip_network", "ip_interface", "v4_int_to_packed", "v6_int_to_packed"},
        *{"summarize_address_range", "collapse_addresses", "get_mixed_type_key"},
        *{"IPv4Address", "IPv4Interface", "IPv4Network", "IPv6Address", "IPv6Interface", "IPv6Network"},
    },
    # --- Project Self-Ref ---
    "structcast.utils.base": {None},  # Allow all attributes from structcast.utils module
}
"""Default allowed modules and their allowed attributes for StructCast instantiation."""

__all__ = [
    "DEFAULT_ALLOWED_DUNDERS",
    "DEFAULT_ALLOWED_MODULES",
    "DEFAULT_BLOCKED_MODULES",
    "DEFAULT_DANGEROUS_DUNDERS",
]


def __dir__() -> list[str]:
    return structcast.utils.security.get_default_dir(globals())
