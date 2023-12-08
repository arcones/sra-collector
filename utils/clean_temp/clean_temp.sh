#!/usr/bin/env bash

rm -rf infra/.terraform
find . -name "*.zip" -type f -delete
find . -name "bundle" -type d -exec rm -r "{}" \;
find infra -name "env_*" -type d -exec rm -r "{}" \;
find . -name ".terraform.lock.hcl" -type f -delete

echo "Temp files and folders have been deleted"
