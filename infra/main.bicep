// Subscription-scope deployment that creates a new resource group and
// then deploys all the demo resources into it (Cosmos DB, Blob Storage,
// Azure OpenAI) plus the data-plane RBAC assignments your user needs to
// run the demos with `DefaultAzureCredential`.

targetScope = 'subscription'

@description('Azure region for the resource group and all resources.')
param location string = 'eastus2'

@description('Name of the new resource group to create.')
param resourceGroupName string = 'rg-sedwick-sidekick'

@description('Short suffix appended to globally-unique resource names. Leave default for a stable name, or override per environment.')
param nameSuffix string = uniqueString(subscription().id, resourceGroupName)

@description('Object id of the user (or service principal) running the demos. Used for data-plane RBAC. Get with: az ad signed-in-user show --query id -o tsv')
param principalId string

@description('Type of the principal receiving RBAC. Use User for `az ad signed-in-user`, ServicePrincipal for an SP/MI.')
@allowed([
  'User'
  'ServicePrincipal'
  'Group'
])
param principalType string = 'User'

@description('Name of the Azure OpenAI chat deployment to create (this is what AZURE_OPENAI_CHAT_MODEL points at).')
param chatDeploymentName string = 'gpt-4o-mini'

@description('Underlying chat model.')
param chatModelName string = 'gpt-4o-mini'

@description('Chat model version.')
param chatModelVersion string = '2024-07-18'

@description('Capacity (TPM in thousands) for the chat deployment.')
param chatModelCapacity int = 30

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
}

module resources 'resources.bicep' = {
  name: 'sedwick-sidekick-resources'
  scope: rg
  params: {
    location: location
    nameSuffix: nameSuffix
    principalId: principalId
    principalType: principalType
    chatDeploymentName: chatDeploymentName
    chatModelName: chatModelName
    chatModelVersion: chatModelVersion
    chatModelCapacity: chatModelCapacity
  }
}

@description('Values to drop into your local .env.')
output env object = {
  AZURE_OPENAI_ENDPOINT: resources.outputs.openAiEndpoint
  AZURE_OPENAI_CHAT_MODEL: chatDeploymentName
  COSMOS_ENDPOINT: resources.outputs.cosmosEndpoint
  COSMOS_DATABASE: resources.outputs.cosmosDatabaseName
  COSMOS_CONTAINER: resources.outputs.cosmosContainerName
  BLOB_ACCOUNT_URL: resources.outputs.blobAccountUrl
  BLOB_CONTAINER: resources.outputs.blobContainerName
}

output resourceGroupName string = rg.name
