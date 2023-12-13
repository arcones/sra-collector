#!/usr/bin/env bash

rm -rf infra/.terraform
find . -name "get_*.zip" -type f -delete
find . -name "paginate_*.zip" -type f -delete
find . -name "bundle" -type d -exec rm -r "{}" \;
find infra -name "env_*" -type d -exec rm -r "{}" \;

echo "Temp files and folders have been deleted"
