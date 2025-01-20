import unittest
import os
import json
import shutil
from tools.filecontentreadertool import FileContentReaderTool


class TestFileContentReaderTool(unittest.TestCase):
    def setUp(self):
        self.tool = FileContentReaderTool()
        self.test_files = []
        self.test_dirs = []

    def tearDown(self):
        # Clean up test files
        for file_path in self.test_files:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"Warning: Could not remove file {file_path}: {e}")

        # Clean up test directories
        for dir_path in self.test_dirs:
            if os.path.exists(dir_path):
                try:
                    shutil.rmtree(dir_path)
                except Exception as e:
                    print(f"Warning: Could not remove directory {dir_path}: {e}")

    def create_test_file(self, filename, content):
        """Helper method to create test files"""
        with open(filename, "w") as f:
            f.write(content)
        self.test_files.append(filename)
        return filename

    def test_initialization(self):
        """Test tool initialization and properties"""
        self.assertEqual(self.tool.name, "filecontentreadertool")
        self.assertIsInstance(self.tool.description, str)
        self.assertIsInstance(self.tool.input_schema, dict)
        self.assertTrue(hasattr(self.tool, "execute"))

    def test_single_file_reading(self):
        """Test reading a single file"""
        test_content = "This is test content"
        filename = self.create_test_file("test_single.txt", test_content)

        result = self.tool.execute(file_paths=[filename])
        result_dict = json.loads(result)

        self.assertIn(filename, result_dict)
        self.assertEqual(result_dict[filename], test_content)

    def test_multiple_files_reading(self):
        """Test reading multiple files"""
        files = {"test1.txt": "Content of file 1", "test2.txt": "Content of file 2"}

        for filename, content in files.items():
            self.create_test_file(filename, content)

        result = self.tool.execute(file_paths=list(files.keys()))
        result_dict = json.loads(result)

        for filename, content in files.items():
            self.assertIn(filename, result_dict)
            self.assertEqual(result_dict[filename], content)

    def test_nonexistent_file(self):
        """Test handling of non-existent files"""
        result = self.tool.execute(file_paths=["nonexistent.txt"])
        result_dict = json.loads(result)

        self.assertIn("nonexistent.txt", result_dict)
        self.assertEqual(result_dict["nonexistent.txt"], "Error: File not found")

    def test_empty_file_list(self):
        """Test handling of empty file list"""
        result = self.tool.execute(file_paths=[])
        result_dict = json.loads(result)

        self.assertEqual(result_dict, {})

    def test_binary_file_handling(self):
        """Test handling of binary files"""
        # Create a simple binary file
        binary_file = "test_binary.bin"
        with open(binary_file, "wb") as f:
            f.write(b"\x00\x01\x02\x03")
        self.test_files.append(binary_file)

        result = self.tool.execute(file_paths=[binary_file])
        result_dict = json.loads(result)

        self.assertIn(binary_file, result_dict)
        self.assertIn("Skipped: Binary", result_dict[binary_file])

    def test_directory_handling(self):
        """Test handling of directory paths"""
        # Create a test directory with some files
        test_dir = "test_dir"
        os.makedirs(test_dir, exist_ok=True)
        self.test_dirs.append(test_dir)  # Add to test_dirs instead of test_files

        # Create some files in the directory
        self.create_test_file(os.path.join(test_dir, "file1.txt"), "Content 1")
        self.create_test_file(os.path.join(test_dir, "file2.txt"), "Content 2")

        result = self.tool.execute(file_paths=[test_dir])
        result_dict = json.loads(result)

        # Verify directory contents were read
        self.assertIsInstance(result_dict, dict)
        self.assertGreater(len(result_dict), 0)

        # Verify specific files were read
        expected_files = [
            os.path.join(test_dir, "file1.txt"),
            os.path.join(test_dir, "file2.txt"),
        ]
        for file_path in expected_files:
            self.assertIn(file_path, result_dict)


if __name__ == "__main__":
    unittest.main()
