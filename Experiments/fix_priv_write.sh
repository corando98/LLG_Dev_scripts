#!/bin/bash

"""
This script is used to remove the ryzenadj commands from the steamos-priv-write file. 
The intend of these commands in the original file is to fix the steamOS qam TDP slider, by mapping the TDP values to the correct values for the Z series processors.
"""


# Path to the steamos-priv-write file
file_path="/usr/bin/steamos-priv-write"

# Temporary file for modifications
temp_file="$(mktemp)"

# Flag to indicate if we are inside the block that needs to be commented
inside_block=0

# Read the file line by line
while IFS= read -r line
do
    # Check if the line starts the block
    if [[ $line == "if [[ -n \$ZSERIES ]]; then" ]]; then
        inside_block=1
        echo "# $line" >> "$temp_file" # Comment out the line
    elif [[ $inside_block -eq 1 && $line == "fi" ]]; then
        inside_block=0
        echo "# $line" >> "$temp_file" # Comment out the line
    elif [[ $inside_block -eq 1 ]]; then
        echo "# $line" >> "$temp_file" # Comment out the line
    else
        echo "$line" >> "$temp_file" # Keep the line as is
    fi
done < "$file_path"

# Replace the original file with the modified one
mv "$temp_file" "$file_path"
