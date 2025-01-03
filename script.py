from tools.filediffmergetool import FileDiffMergeTool

def analyze_differences():
    # Initialize the diff tool
    diff_tool = FileDiffMergeTool()
    
    # Files to compare
    file1 = "ce3_new.py"
    file2 = "ce3_with_memory.py"
    
    try:
        # Get semantic differences
        differences = diff_tool.get_semantic_diff(file1, file2)
        
        # Generate structured output
        print("\nKey Differences Analysis:")
        print("=" * 50)
        
        # Print differences by category
        categories = ["imports", "class_definitions", "methods", "functionality"]
        for category in categories:
            if category in differences:
                print(f"\n{category.title()} Changes:")
                print("-" * 30)
                for diff in differences[category]:
                    print(f"- {diff}")
        
        # Print merge recommendations
        print("\nMerge Recommendations:")
        print("=" * 50)
        merge_suggestions = diff_tool.get_merge_recommendations(file1, file2)
        for suggestion in merge_suggestions:
            print(f"- {suggestion}")
            
    except Exception as e:
        print(f"Error analyzing differences: {e}")

if __name__ == "__main__":
    analyze_differences()

