#!/bin/bash

# Script to rename all files in folders containing .shp files to match the folder name
# Usage: ./rename_shp.sh [target_path]

# Set default target path to current directory if not provided
if [ $# -eq 0 ]; then
    TARGET_PATH="."
else
    TARGET_PATH="$1"
fi

# Check if the target path exists
if [ ! -d "$TARGET_PATH" ]; then
    echo "Error: Target path '$TARGET_PATH' does not exist."
    exit 1
fi

echo "Processing folders in '$TARGET_PATH'..."

# Find all directories (including the target path itself) and process them
find "$TARGET_PATH" -type d | while read -r folder; do
    # Skip if folder is not readable
    if [ ! -r "$folder" ]; then
        continue
    fi
    
    # Find .shp files in this folder
    shp_files=$(find "$folder" -maxdepth 1 -name "*.shp" -type f)
    
    # Count .shp files
    shp_count=$(echo "$shp_files" | wc -l)
    
    # If at least one .shp file exists, rename all files in the folder
    if [ "$shp_count" -gt 0 ]; then
        # Get the folder name
        folder_name=$(basename "$folder")
        
        echo "Found .shp files in '$folder', renaming all files to '$folder_name'"
        
        # Get all files in the folder (excluding subdirectories)
        all_files=$(find "$folder" -maxdepth 1 -type f)
        
        # Process each file
        while IFS= read -r file; do
            # Skip if it's the script itself
            if [ "$(basename "$file")" = "$(basename "$0")" ]; then
                continue
            fi
            
            # Get the directory of the file
            file_dir=$(dirname "$file")
            
            # Get the extension of the file
            file_ext="${file##*.}"
            
            # Get the base name of the file (without extension)
            file_base="${file%.*}"
            
            # Create the new file name with folder name
            new_file_name="$file_dir/$folder_name.$file_ext"
            
            # Check if a file with the new name already exists
            if [ -f "$new_file_name" ]; then
                echo "Warning: File '$new_file_name' already exists. Skipping '$file'."
                continue
            fi
            
            # Rename the file
            echo "Renaming '$file' to '$new_file_name'"
            mv "$file" "$new_file_name"
            
            if [ $? -eq 0 ]; then
                echo "Successfully renamed '$(basename "$file")' to '$(basename "$new_file_name")'"
            else
                echo "Error: Failed to rename file '$file'."
            fi
        done <<< "$all_files"
    fi
done

echo "Processing complete."