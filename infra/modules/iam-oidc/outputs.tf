output "ebs_csi_role_arn" {
  value = module.ebs_csi_irsa.iam_role_arn
}

output "lb_controller_role_arn" {
  value = module.lb_controller_irsa.iam_role_arn
}
