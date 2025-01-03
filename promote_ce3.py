from code_manager import CodeManager
import shutil
from datetime import datetime
import sys

def main():
    try:
        # Initialize CodeManager
        manager = CodeManager('ce3.py')
        
        # Ensure code_manager.py is in version control
        print("Checking version control setup...")
        if not manager.version_control.is_tracked('code_manager.py'):
            print("Adding code_manager.py to version control...")
            if not manager.version_control.add_file('code_manager.py'):
                sys.exit("Failed to add code_manager.py to version control")
        
        # Create backup of current ce3.py
        print("Creating backup...")
        backup_file = manager._create_backup()
        if not backup_file:
            sys.exit("Failed to create backup")

        print("Promoting ce3_new.py to ce3.py")
        # Unlock target file first
        manager._unlock_file()

        # Copy new file to target
        shutil.copy2("ce3_new.py", "ce3.py")

        # Lock the target file
        manager._lock_file()

        print("Adding ce3.py to version control...")
        try:
            success = manager.version_control.add_file('ce3.py')
            if not success:
                sys.exit("Failed to add ce3.py to version control")
        except Exception as e:
            sys.exit(f"Error adding ce3.py: {str(e)}")

        print("Committing changes to version control")
        try:
            success = manager.version_control.commit_changes(['ce3.py'], 
                "Promoted ce3_new.py with cache functionality to ce3.py")
            if not success:
                sys.exit("Failed to commit changes")
        except Exception as e:
            sys.exit(f"Error committing changes: {str(e)}")
        
        print("Successfully promoted ce3_new.py to ce3.py")
        print(f"Backup saved as: {backup_file}")
        
    except Exception as e:
        print(f"Error during promotion: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()

