from tools.filecontentreadertool import FileContentReaderTool
import json
import os


def test_file_reader():
    # Initialize the tool
    tool = FileContentReaderTool()
    print(f"Initialized {tool.name}")

    # Create a test file
    test_file_path = "test_content.txt"
    test_content = "This is a test file content"
    with open(test_file_path, "w") as f:
        f.write(test_content)

    try:
        # Test case 1: Read single file
        print("\nTest 1: Reading single file")
        result = tool.execute(file_paths=[test_file_path])
        result_dict = json.loads(result)
        print(f"Content of {test_file_path}:")
        print(result_dict[test_file_path])

        # Test case 2: Read non-existent file
        print("\nTest 2: Reading non-existent file")
        result = tool.execute(file_paths=["nonexistent.txt"])
        result_dict = json.loads(result)
        print(result_dict)

        # Test case 3: Read multiple files
        second_file = "test_content2.txt"
        with open(second_file, "w") as f:
            f.write("Content of second file")

        print("\nTest 3: Reading multiple files")
        result = tool.execute(file_paths=[test_file_path, second_file])
        result_dict = json.loads(result)
        print("Contents of multiple files:")
        print(json.dumps(result_dict, indent=2))

    finally:
        # Cleanup
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
        if os.path.exists(second_file):
            os.remove(second_file)


if __name__ == "__main__":
    test_file_reader()
