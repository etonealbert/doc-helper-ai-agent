$ErrorActionPreference = "Stop"

$terraformRoot = Split-Path -Parent $PSScriptRoot
$bootstrapRoot = Join-Path $terraformRoot "bootstrap"
$devRoot = Join-Path $terraformRoot "environments/dev"

terraform fmt -check -recursive $terraformRoot
terraform -chdir=$bootstrapRoot init -backend=false -input=false
terraform -chdir=$bootstrapRoot validate
terraform -chdir=$devRoot init -backend=false -input=false
terraform -chdir=$devRoot validate
