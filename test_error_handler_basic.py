from tools.errorhandlertool import ErrorHandlerTool


def test_error_handler():
    # Initialize the tool
    tool = ErrorHandlerTool()
    print(f"Initialized {tool.name}")

    # Test case 1: Basic error handling
    test_errors = [
        "Error 1: Something went wrong",
        "Error 1: Something went wrong",  # Duplicate
        "Error 2: Another issue occurred",
    ]

    print("\nTest 1: Basic error handling")
    result = tool.execute(error_messages=test_errors)
    print(result)

    # Test case 2: System trace handling
    test_errors_with_trace = [
        "Error: Application error",
        "Traceback (most recent call last):\n  File 'test.py', line 10",
    ]

    print("\nTest 2: System trace handling (excluded)")
    result = tool.execute(error_messages=test_errors_with_trace, include_traces=False)
    print(result)

    print("\nTest 2b: System trace handling (included)")
    result = tool.execute(error_messages=test_errors_with_trace, include_traces=True)
    print(result)


if __name__ == "__main__":
    test_error_handler()
