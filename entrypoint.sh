#!/bin/bash

set -e
if [ -z "$INPUT_PATH" ]; then
    echo "❌ Error: 'path' input is required"
    exit 1
fi
if [ -z "$INPUT_AUTH_METHOD" ]; then
    echo "❌ Error: 'auth-method' input is required"
    exit 1
fi
if [ "$INPUT_AUTH_METHOD" = "password" ]; then
    if [ -z "$INPUT_USERNAME" ] || [ -z "$INPUT_PASSWORD" ]; then
        echo "❌ Error: 'username' and 'password' are required when using password authentication"
        exit 1
    fi
elif [ "$INPUT_AUTH_METHOD" = "webdev" ]; then
    if [ -z "$INPUT_AUTHORIZATION" ]; then
        echo "❌ Error: 'authorization' is required when using webdev authentication"
        exit 1
    fi
else
    echo "❌ Error: Invalid auth-method. Must be 'password' or 'webdev'"
    exit 1
fi
if [ ! -e "$INPUT_PATH" ]; then
    echo "❌ Error: Upload path '$INPUT_PATH' does not exist"
    exit 1
fi
# echo "📋 Configuration:"
# echo "  - Auth Method: $INPUT_AUTH_METHOD"
# echo "  - Upload Path: $INPUT_PATH"
# echo "  - Destination: ${INPUT_DESTINATION:-'(root)'}"
# echo "  - Conflict Strategy: ${INPUT_CONFLICT_STRATEGY:-'keep-both'}"
python /app/src/main.py
