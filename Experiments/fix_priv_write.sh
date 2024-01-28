#!/bin/bash

#This script is used to remove the ryzenadj commands from the steamos-priv-write file. 
#The intend of these commands in the original file is to fix the steamOS qam TDP slider, by mapping the TDP values to the correct values for the Z series processors.



# Path to the steamos-priv-write file
file_path="/usr/bin/steamos-polkit-helpers/steamos-priv-write"

# Temporary file for modifications
temp_file="$(mktemp)"

# Flag to indicate if we are inside the block that needs to be commented
inside_block=0

# Read the file line by line
while IFS= read -r line
do
    # echo "Checking $line"
    # Check if the line starts the block
    if [[ "$line" =~ if\ \[\[\ -n\ \$ZSERIES\ \]\]\; ]]; then
        # Start of the block to be commented
        comment_flag=1
    fi

    if [[ $comment_flag -eq 1 ]]; then
        # Comment out the line
        echo "#$line" >> "$temp_file"
    else
        # Keep the line as is
        echo "$line" >> "$temp_file"
    fi

    # Check for end of the block
    if [[ $comment_flag -eq 1 && "$line" == "fi" ]]; then
        # End of the block to be commented
        comment_flag=0
    fi
done < "$file_path"
echo "Done, restart steam to apply changes"

# Replace the original file with the modified one
mv "$temp_file" "$file_path"
chmod 777 "$file_path"