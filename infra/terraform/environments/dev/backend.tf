terraform {
  backend "s3" {
    bucket       = "albertlukmanovlabs-terraform-state-964866958896"
    key          = "doc-helper-ai-agent/dev/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}
