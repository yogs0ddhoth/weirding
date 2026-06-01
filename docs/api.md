# API Reference

## Core pipeline

::: weirding
    options:
      members:
        - compile
        - define_model
        - from_schema
        - parse
        - to_xml

## Prompt utilities

::: weirding.prompt
    options:
      members:
        - to_template
        - format_error
        - RetryContext

## Protocols and types

::: weirding
    options:
      members:
        - JsonSchemaIR
        - DTOBuilder
        - PydanticBuilder
        - Validatable

## Exceptions

::: weirding
    options:
      members:
        - WeirdingError
        - SchemaError
        - ParseError
        - UnsupportedDialectError
