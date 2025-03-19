#!/usr/bin/env zsh

# Redirect stderr to temporary log file while preserving fd 3
exec 3>&2
exec 2>/tmp/summary_debug.log

# File extensions to process - focused on JFK Files Scraper project
SOURCE_EXTENSIONS=(".md" ".py" ".json" ".csv")
CONFIG_EXTENSIONS=(".json" ".yml" ".yaml" ".envrc")
ALL_EXTENSIONS=("${SOURCE_EXTENSIONS[@]}" "${CONFIG_EXTENSIONS[@]}")

# Important directories to include
IMPORTANT_DIRS=(
    "json"
    "markdown"
    "pdfs"
    "scripts"
    "src"
    "src/utils"
    "tests"
    "metrics"
    "metrics/charts"
)

# Directories to exclude
EXCLUDE_DIRS=(
    ".git"
    "venv"
    ".env"
    ".venv"
    "__pycache__"
    "build"
    "dist"
    ".pytest_cache"
    ".idea"
    ".vscode"
    ".checkpoints"
)

# Files to exclude
EXCLUDE_FILES=(
    "*.lock"
    "coverage.*"
    ".DS_Store"
    "*.pyc"
    "*.pyo"
    "*.pyd"
    "*_test.log"
    "*_result.txt"
)

# Important specific files to always include
IMPORTANT_FILES=(
    "docs/README.md"
    "docs/TASKLIST.md"
    "docs/CONSOLIDATED_TASKS.md"
    ".clinerules"
    ".envrc"
    "src/jfk_scraper.py"
    "scripts/run_test.py"
    "src/optimization.py"
    "src/performance_monitoring.py"
    "src/utils/storage.py"
)

# Function to check if OpenAI API key is available
check_openai_api_key() {
    if [[ -z "${OPENAI_API_KEY}" ]]; then
        echo "Error: Missing required environment variable OPENAI_API_KEY" >&3
        return 1
    fi
    
    return 0
}

# Function to check if a file is in the important files list
is_important_file() {
    local file="$1"
    
    for important_file in "${IMPORTANT_FILES[@]}"; do
        if [[ "$file" == "$important_file" ]]; then
            return 0
        fi
    done
    
    return 1
}

# Function to check if a file is in an important directory
is_in_important_dir() {
    local file="$1"
    
    for important_dir in "${IMPORTANT_DIRS[@]}"; do
        if [[ "$file" == $important_dir/* ]]; then
            return 0
        fi
    done
    
    return 1
}

# Function to generate tree structure
generate_tree_structure() {
    local -a files=("$@")
    local output=""
    local prev_dir=""
    local indent=""
    
    # Sort files to ensure consistent ordering
    files=(${(on)files})
    
    # First, identify all unique top-level directories
    typeset -A top_dirs
    for file in "${files[@]}"; do
        local top_dir=${file%%/*}
        if [[ "$top_dir" != "." ]]; then
            top_dirs[$top_dir]=1
        fi
    done
    
    # Process files by top-level directory
    for top_dir in ${(k)top_dirs}; do
        output+="├── $top_dir/\n"
        
        # Process files in this top-level directory
        local first_in_dir=1
        for file in "${files[@]}"; do
            if [[ "$file" == $top_dir/* ]]; then
                # Split path into directory and filename
                local dir=${file%/*}
                local filename=${file##*/}
                local rel_dir=${dir#$top_dir/}
                
                # If we're in a new subdirectory, print it
                if [[ "$rel_dir" != "$prev_dir" && "$rel_dir" != "." && "$rel_dir" != "$top_dir" ]]; then
                    # Calculate indent based on subdirectory depth
                    local depth=$(($(echo "$rel_dir" | tr -cd '/' | wc -c) + 1))
                    indent=$(printf "%$((depth * 4))s" "")
                    
                    # Print each subdirectory in the path
                    local current=""
                    for d in ${(s:/:)rel_dir}; do
                        if [[ -n "$current" ]]; then
                            current+="/"
                        fi
                        current+="$d"
                        
                        if [[ "$current" != "$prev_dir"* ]]; then
                            local d_indent=$(printf "%$((($(echo "$current" | tr -cd '/' | wc -c) + 1) * 4))s" "")
                            output+="${d_indent}├── $d/\n"
                        fi
                    done
                    prev_dir="$rel_dir"
                fi
                
                # Print the file
                if [[ "$dir" == "$top_dir" ]]; then
                    output+="    └── $filename\n"
                else
                    output+="${indent}    └── $filename\n"
                fi
            fi
        done
    done
    
    # Process root-level files
    for file in "${files[@]}"; do
        if [[ "$file" != */* ]]; then
            output+="└── $file\n"
        fi
    done
    
    echo "$output"
}

# Function to collect files
collect_files() {
    local files=()
    local exclude_pattern=""
    
    # Build exclude pattern
    for dir in "${EXCLUDE_DIRS[@]}"; do
        exclude_pattern+=" -not -path '*/$dir/*'"
    done
    
    for pattern in "${EXCLUDE_FILES[@]}"; do
        exclude_pattern+=" -not -name '$pattern'"
    done
    
    # First add all important files
    for file in "${IMPORTANT_FILES[@]}"; do
        if [[ -f "$file" ]]; then
            files+=("$file")
        fi
    done
    
    # Find files with specified extensions in important directories
    for dir in "${IMPORTANT_DIRS[@]}"; do
        if [[ -d "$dir" ]]; then
            for ext in "${ALL_EXTENSIONS[@]}"; do
                while IFS= read -r file; do
                    if [[ -n "$file" ]]; then
                        files+=("${file#./}")
                    fi
                done < <(eval "find $dir -type f -name '*$ext' $exclude_pattern" 2>/dev/null)
            done
        fi
    done
    
    # Find core configuration files at the root level
    for ext in "${CONFIG_EXTENSIONS[@]}"; do
        while IFS= read -r file; do
            if [[ -n "$file" && ! "$file" =~ "/" ]]; then
                files+=("${file#./}")
            fi
        done < <(eval "find . -maxdepth 1 -type f -name '*$ext' $exclude_pattern" 2>/dev/null)
    done
    
    # Deduplicate files
    typeset -A unique_files
    for file in "${files[@]}"; do
        unique_files[$file]=1
    done
    
    echo "${(k)unique_files}"
}

# Main script
main() {
    local output_file="jfk-files-project-overview.txt"
    
    # Debug output
    echo "Using OPENAI_API_KEY from environment" >&3
    
    # Check OpenAI API key
    if ! check_openai_api_key; then
        exit 1
    fi
    
    echo "Generating JFK Files Scraper project overview..." >&3
    
    # Collect files
    local -a files=($(collect_files))
    
    if (( ${#files} == 0 )); then
        echo "No files found matching the criteria" >&3
        exit 1
    fi
    
    # Generate output
    {
        echo "JFK Files Scraper Project Overview"
        echo "=================================="
        echo
        echo "This overview focuses on the core components of the JFK Files Scraper project,"
        echo "a tool for scraping JFK files from the National Archives, processing PDF documents"
        echo "to Markdown and JSON formats for use as a Lite LLM dataset."
        echo
        echo "Directory Structure:"
        echo "------------------"
        generate_tree_structure "${files[@]}"
        echo
        echo "Key Components:"
        echo "--------------"
        echo "- Scraper: Python-based tool for extracting JFK files from National Archives"
        echo "- PDF Processing: Download and conversion of PDF files to structured formats"
        echo "- JSON Generation: Creation of properly formatted JSON for LLM use"
        echo "- Performance Monitoring: Tools for tracking and optimizing processing"
        echo "- Documentation: Project documentation and progress tracking"
        echo
        echo "File Contents:"
        echo "-------------"
        
        # First include key files
        for file in "${files[@]}"; do
            if [[ "$file" == "src/jfk_scraper.py" ]]; then
                echo
                echo "### $file"
                echo "\`\`\`python"
                cat "$file" 2>/dev/null || echo "Error: Unable to read file"
                echo "\`\`\`"
            fi
        done
        
        # Then include README files
        for file in "${files[@]}"; do
            if [[ "$file" == *"README.md" ]]; then
                echo
                echo "### $file"
                echo "\`\`\`markdown"
                cat "$file" 2>/dev/null || echo "Error: Unable to read file"
                echo "\`\`\`"
            fi
        done
        
        # Then include core configuration files
        for file in "${files[@]}"; do
            if [[ "$file" == *"config.js" || "$file" == "package.json" || "$file" == "vite.config.ts" || "$file" == "tsconfig.json" ]]; then
                echo
                echo "### $file"
                echo "\`\`\`${file##*.}"
                cat "$file" 2>/dev/null || echo "Error: Unable to read file"
                echo "\`\`\`"
            fi
        done
        
        # Then include source files
        for file in "${files[@]}"; do
            if [[ "$file" == "src/"*".py" ]]; then
                echo
                echo "### $file"
                echo "\`\`\`python"
                cat "$file" 2>/dev/null || echo "Error: Unable to read file"
                echo "\`\`\`"
            fi
        done
        
        # Then include test files
        for file in "${files[@]}"; do
            if [[ "$file" == "tests/"*".py" ]]; then
                echo
                echo "### $file"
                echo "\`\`\`python"
                cat "$file" 2>/dev/null || echo "Error: Unable to read file"
                echo "\`\`\`"
            fi
        done
        
        # Then include a sample of JSON files
        local json_count=0
        for file in "${files[@]}"; do
            if [[ "$file" == "json/"*".json" && "$json_count" -lt 3 ]]; then
                echo
                echo "### $file (Sample JSON)"
                echo "\`\`\`json"
                cat "$file" 2>/dev/null || echo "Error: Unable to read file"
                echo "\`\`\`"
                ((json_count++))
            fi
        done
        
        # Then include a sample of Markdown files
        local md_count=0
        for file in "${files[@]}"; do
            if [[ "$file" == "markdown/"*".md" && "$md_count" -lt 3 ]]; then
                echo
                echo "### $file (Sample Markdown)"
                echo "\`\`\`markdown"
                cat "$file" 2>/dev/null || echo "Error: Unable to read file"
                echo "\`\`\`"
                ((md_count++))
            fi
        done
        
        # Then include other script files and important Python files
        for file in "${files[@]}"; do
            if [[ "$file" != *"README.md" && 
                  "$file" != "src/jfk_scraper.py" &&
                  "$file" != "src/"*".py" && 
                  "$file" != "tests/"*".py" &&
                  "$file" != "json/"*".json" && "$file" != "markdown/"*".md" ]]; then
                
                # Process Python and script files
                if [[ "$file" == *".py" || "$file" == "scripts/"* ]]; then
                    echo
                    echo "### $file"
                    ext="${file##*.}"
                    if [[ "$ext" == "py" ]]; then
                        echo "\`\`\`python"
                    elif [[ "$ext" == "sh" ]]; then
                        echo "\`\`\`bash"
                    else
                        echo "\`\`\`${ext}"
                    fi
                    cat "$file" 2>/dev/null || echo "Error: Unable to read file"
                    echo "\`\`\`"
                fi
            fi
        done
    } > "$output_file"
    
    echo "JFK Files Scraper project overview has been written to $output_file" >&3
}

# Run main function
main

# Restore original stderr
exec 2>&3
exec 3>&-