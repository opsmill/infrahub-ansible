#!/bin/bash

# Define the directory to search
directory_to_search="."
script_name=$(basename "$0")

# Find all files and replace patterns
grep -rl "_API" "$directory_to_search" | grep -v "$script_name" | while read -r file; do
    sed -i '' 's/INFRAHUB_API/INFRAHUB_ADDRESS/g' "$file"
    sed -i '' 's/INFRAHUB\\_API/INFRAHUB_ADDRESS/g' "$file"
    echo "Replaced patterns in: $file"
done

grep -rl "_TOKEN" "$directory_to_search" | grep -v "$script_name" | while read -r file; do
    sed -i '' 's/INFRAHUB_TOKEN/INFRAHUB_API_TOKEN/g' "$file"
    sed -i '' 's/INFRAHUB\\_TOKEN/INFRAHUB_API_TOKEN/g' "$file"
    echo "Replaced patterns in: $file"
done