#!/usr/bin/env bash

userpoolid="$1"
username="$2"
password="$3"

aws cognito-idp admin-create-user  --user-pool-id $userpoolid --username $username --message-action SUPPRESS --force-alias-creation --region eu-central-1 | cat && \
  aws cognito-idp admin-set-user-password --user-pool-id $userpoolid --username $username --password $password --permanent  --region eu-central-1 | cat && \
    aws ses verify-email-identity --email-address $username --region eu-central-1 --output json
