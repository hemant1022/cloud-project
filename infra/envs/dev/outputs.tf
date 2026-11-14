output "cluster_name" {
  value = module.eks.cluster_name
}

output "cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "region" {
  value = var.region
}

output "vpc_id" {
  value = module.vpc.vpc_id
}

output "ebs_csi_role_arn" {
  value = module.iam_oidc.ebs_csi_role_arn
}

output "lb_controller_role_arn" {
  value = module.iam_oidc.lb_controller_role_arn
}

output "configure_kubectl" {
  value = "aws eks update-kubeconfig --name ${module.eks.cluster_name} --region ${var.region}"
}
