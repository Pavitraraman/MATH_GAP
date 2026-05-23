class LLMProviderError(RuntimeError):
    """Raised when the external LLM provider cannot return a valid response."""


class StudentNotFoundError(ValueError):
    """Raised when a student profile could not be found or has no recorded data."""


