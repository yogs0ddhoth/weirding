class RetryContext:
    def __init__(self) -> None:
        raise NotImplementedError


def to_template() -> str:
    raise NotImplementedError


def format_error(error: Exception) -> str:
    raise NotImplementedError
