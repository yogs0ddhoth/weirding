class WeirdingError(Exception):
    pass


class UnsupportedDialectError(WeirdingError):
    pass


class ParseError(WeirdingError):
    pass


class SchemaError(WeirdingError):
    pass
