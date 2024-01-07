#!/usr/bin/env bash

rm -rf infra/.terraform
find . -name "*.zip" -type f -delete
find . -name "bundle" -type d -exec rm -r "{}" \;
find . -name "builds" -type d -exec rm -r "{}" \;

echo "Temp files and folders have been deleted"
