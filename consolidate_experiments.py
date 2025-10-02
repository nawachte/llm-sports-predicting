import os

def consolidate_standardized_notes():
    """
    Traverses the current directory and its subdirectories to find standardized
    experiment overview files and consolidates their content into a single file.

    This script is designed to be placed and run from within the root 
    folder containing all experiment subfolders (e.g., the '/tests' directory).
    """
    # --- Configuration ---
    # The specific suffix that identifies the main experiment file.
    identifier_suffix = '_experiment_overview.txt'
    
    # The name of the consolidated output file.
    # This file will be created in the directory where the script is run.
    output_filename = 'experiment_consolidation.txt'
    
    # The starting point for the search ('.' denotes the current directory).
    root_directory = '.'
    
    files_found = 0

    try:
        with open(output_filename, 'w', encoding='utf-8') as outfile:
            # Walk through the directory tree starting from the current location.
            for dirpath, _, filenames in os.walk(root_directory):
                for filename in filenames:
                    # Check if the filename ends with our specific identifier.
                    if filename.endswith(identifier_suffix):
                        print(f"processing {filename}")
                        files_found += 1
                        
                        # Construct the full path to the file.
                        file_path = os.path.join(dirpath, filename)
                        
                        # Write a clear delimiter to distinguish between experiments.
                        outfile.write(f"--- START OF FILE: {file_path} ---\n\n")
                        
                        # Open and read the content of the identified file.
                        # 'errors='ignore'' prevents issues with potential encoding errors.
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as infile:
                            outfile.write(infile.read())
                        
                        # Write a closing delimiter for clarity.
                        outfile.write(f"\n\n--- END OF FILE: {file_path} ---\n\n")
                        
                        
        if files_found > 0:
            print(f"Consolidation successful. {files_found} experiment files were processed.")
            print(f"Output saved to: {os.path.abspath(output_filename)}")
        else:
            print("Consolidation complete, but no files matching the pattern "
                  f"'{identifier_suffix}' were found in the current directory or its subdirectories.")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# --- Execution ---
# To run the process, simply execute this script.
if __name__ == "__main__":
    consolidate_standardized_notes()