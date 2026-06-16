using 'main.bicep'

// Edit these for your environment, or override on the CLI with --parameters key=value
param location = 'eastus2'
param resourceGroupName = 'rg-workflow-skills-agent-framework-demo-sidekick'

// REQUIRED: object id of the user/SP running the demos.
// Get with: az ad signed-in-user show --query id -o tsv
param principalId = ''
param principalType = 'User'

param chatDeploymentName = 'gpt-4o-mini'
param chatModelName = 'gpt-4o-mini'
param chatModelVersion = '2024-07-18'
param chatModelCapacity = 30
