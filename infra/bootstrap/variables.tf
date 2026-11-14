variable "project" {
  description = "Project name used in resource names."
  type        = string
  default     = "cloud-project"
}

variable "region" {
  description = "AWS region for the state bucket and lock table."
  type        = string
  default     = "us-east-1"
}
