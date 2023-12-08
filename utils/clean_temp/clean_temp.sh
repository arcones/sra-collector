#!/usr/bin/env bash

rm -rf infra/.terraform
find . -name "*.zip" -type f -delete

echo "Temp files and folders have been deleted"
