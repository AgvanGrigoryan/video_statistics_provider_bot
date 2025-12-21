class NLPParseError(Exception):
    """Error in parsing or validating the NL request.

    Used for:
        - LLM errors (invalid structure)
        - Validation errors of values (dates, numbers)
        - Semantic errors (non-existent fields)
    """
    pass

