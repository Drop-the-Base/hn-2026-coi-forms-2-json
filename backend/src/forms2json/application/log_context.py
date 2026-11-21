from contextvars import ContextVar

# Set by the use cases; the logging filter from bootstrap adds it to every log line (NFR-14).
job_id_var: ContextVar[str] = ContextVar("job_id", default="-")
