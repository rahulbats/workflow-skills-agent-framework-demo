<#
.SYNOPSIS
    Deploy the workflow-skills-agent-framework-demo demo infrastructure (new RG + Cosmos + Blob + AOAI)
    and write a ready-to-use .env file at the repo root.

.EXAMPLE
    ./infra/deploy.ps1 -Location eastus2 -ResourceGroupName rg-workflow-skills-agent-framework-demo

.NOTES
    Requires the Azure CLI (`az`) and that you've already run `az login`.
#>
[CmdletBinding()]
param(
    [string] $Location = 'eastus2',
    [string] $ResourceGroupName = 'rg-workflow-skills-agent-framework-demo',
    [string] $DeploymentName = "workflow-skills-agent-framework-demo-$(Get-Date -Format yyyyMMddHHmmss)"
)

$ErrorActionPreference = 'Stop'

Write-Host "==> Resolving signed-in user object id..." -ForegroundColor Cyan
$principalId = az ad signed-in-user show --query id -o tsv
if (-not $principalId) {
    throw "Could not resolve signed-in user. Run 'az login' first."
}
Write-Host "    principalId = $principalId"

$infraDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $infraDir

Write-Host "==> Deploying Bicep (subscription scope)..." -ForegroundColor Cyan
$deploymentJson = az deployment sub create `
    --name $DeploymentName `
    --location $Location `
    --template-file (Join-Path $infraDir 'main.bicep') `
    --parameters (Join-Path $infraDir 'main.bicepparam') `
    --parameters principalId=$principalId resourceGroupName=$ResourceGroupName location=$Location `
    --output json | ConvertFrom-Json

if (-not $deploymentJson) {
    throw "Deployment failed."
}

$envValues = $deploymentJson.properties.outputs.env.value

Write-Host "==> Writing .env at repo root..." -ForegroundColor Cyan
$envPath = Join-Path $repoRoot '.env'
$envLines = @(
    "AZURE_OPENAI_ENDPOINT=$($envValues.AZURE_OPENAI_ENDPOINT)",
    "AZURE_OPENAI_CHAT_MODEL=$($envValues.AZURE_OPENAI_CHAT_MODEL)",
    "COSMOS_ENDPOINT=$($envValues.COSMOS_ENDPOINT)",
    "COSMOS_DATABASE=$($envValues.COSMOS_DATABASE)",
    "COSMOS_CONTAINER=$($envValues.COSMOS_CONTAINER)",
    "BLOB_ACCOUNT_URL=$($envValues.BLOB_ACCOUNT_URL)",
    "BLOB_CONTAINER=$($envValues.BLOB_CONTAINER)"
)
$envLines | Set-Content -Path $envPath -Encoding UTF8

Write-Host ""
Write-Host "Deployment complete." -ForegroundColor Green
Write-Host "  Resource group : $($deploymentJson.properties.outputs.resourceGroupName.value)"
Write-Host "  .env written to: $envPath"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  python -m shared.seed_data"
Write-Host "  python -m demo1_orchestrator_workflow.main CLM-1001"
Write-Host "  python -m demo2_single_agent_tools.main CLM-1001"
