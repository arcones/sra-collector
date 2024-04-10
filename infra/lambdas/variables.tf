variable "queues" {
  type = object({
    A_user_query_sqs = object({
      A_user_query_sqs_arn                = string
      A_user_query_sqs_visibility_timeout = number
    }),
    A_to_B_DLQ_arn = string,
    B_query_pages_sqs = object({
      B_query_pages_sqs_arn                = string
      B_query_pages_sqs_visibility_timeout = number
    }),
    B_to_C_DLQ_arn = string,
    C_study_ids_sqs = object({
      C_study_ids_sqs_arn                = string
      C_study_ids_sqs_visibility_timeout = number
    }),
    C_to_D_DLQ_arn = string,
    D_geos_sqs = object({
      D_geos_sqs_arn                = string
      D_geos_sqs_visibility_timeout = number
    }),
    D_to_E_DLQ_arn = string,
    E_srps_sqs = object({
      E_srps_sqs_arn                = string
      E_srps_sqs_visibility_timeout = number
    }),
    E_to_F_DLQ_arn = string,
    F_srrs_sqs = object({
      F_srrs_sqs_arn                = string
      F_srrs_sqs_visibility_timeout = number
    }),
    F_to_G_DLQ_arn = string,
    G_srr_metadata = object({
      G_srr_metadata_arn                = string
      G_srr_metadata_visibility_timeout = number
    })
    G_to_H_DLQ_arn = string,
    H_user_feedback = object({
      H_user_feedback_arn                = string
      H_user_feedback_visibility_timeout = number
    }),
    H_to_mail_DLQ_arn = string,
  })
}

variable "aws_apigatewayv2_api_execution_arn" {
  type = string
}

variable "s3_code_bucket_id" {
  type = string
}

variable "s3_reports_bucket_arn" {
  type = string
}

variable "ncbi_api_key_secret_arn" {
  type = string
}

variable "rds_kms_key_arn" {
  type = string
}

variable "cloudwatch_to_opensearch_function_arn" {
  type = string
}

variable "cognito_pool_id" {
  type = string
}

variable "cognito_client_id" {
  type = string
}

variable "webmaster_mail" {
  default = null
  type    = string
}
