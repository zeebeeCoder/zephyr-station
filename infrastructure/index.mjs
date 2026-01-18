// Pulumi stack - REST API v1 with API keys

import * as pulumi from '@pulumi/pulumi';
import * as aws from '@pulumi/aws';

// Configuration
const config = new pulumi.Config();
const databaseUrl = config.requireSecret('databaseUrl');

// Get current region
const region = aws.getRegionOutput();

// =============================================================================
// IAM Role for Lambda
// =============================================================================

const lambdaRole = new aws.iam.Role('zephyr-api-role', {
  assumeRolePolicy: JSON.stringify({
    Version: '2012-10-17',
    Statement: [{
      Action: 'sts:AssumeRole',
      Effect: 'Allow',
      Principal: { Service: 'lambda.amazonaws.com' },
    }],
  }),
});

new aws.iam.RolePolicyAttachment('zephyr-api-logs', {
  role: lambdaRole.name,
  policyArn: aws.iam.ManagedPolicy.AWSLambdaBasicExecutionRole,
});

// =============================================================================
// Lambda Function
// =============================================================================

const lambda = new aws.lambda.Function('zephyr-api', {
  runtime: 'nodejs20.x',
  handler: 'handler.handler',
  role: lambdaRole.arn,
  code: new pulumi.asset.AssetArchive({
    'handler.js': new pulumi.asset.FileAsset('./dist/handler.js'),
  }),
  architectures: ['arm64'],
  timeout: 15,
  memorySize: 256,
  environment: {
    variables: {
      DATABASE_URL: databaseUrl,
      ENVIRONMENT: 'dev',
    },
  },
});

// =============================================================================
// REST API v1
// =============================================================================

const api = new aws.apigateway.RestApi('zephyr-api', {
  name: 'zephyr-api',
  description: 'Zephyr Weather Station API',
  apiKeySource: 'HEADER',
});

// =============================================================================
// /hello Resource (Health Check - No API Key)
// =============================================================================

const helloResource = new aws.apigateway.Resource('hello-resource', {
  restApi: api.id,
  parentId: api.rootResourceId,
  pathPart: 'hello',
});

const helloMethod = new aws.apigateway.Method('hello-method', {
  restApi: api.id,
  resourceId: helloResource.id,
  httpMethod: 'GET',
  authorization: 'NONE',
  apiKeyRequired: false,
});

const helloIntegration = new aws.apigateway.Integration('hello-integration', {
  restApi: api.id,
  resourceId: helloResource.id,
  httpMethod: helloMethod.httpMethod,
  integrationHttpMethod: 'POST',
  type: 'AWS_PROXY',
  uri: lambda.invokeArn,
});

// =============================================================================
// /ingest Resource (Sensor Data - API Key Required)
// =============================================================================

const ingestResource = new aws.apigateway.Resource('ingest-resource', {
  restApi: api.id,
  parentId: api.rootResourceId,
  pathPart: 'ingest',
});

const ingestMethod = new aws.apigateway.Method('ingest-method', {
  restApi: api.id,
  resourceId: ingestResource.id,
  httpMethod: 'POST',
  authorization: 'NONE',
  apiKeyRequired: true,
});

const ingestIntegration = new aws.apigateway.Integration('ingest-integration', {
  restApi: api.id,
  resourceId: ingestResource.id,
  httpMethod: ingestMethod.httpMethod,
  integrationHttpMethod: 'POST',
  type: 'AWS_PROXY',
  uri: lambda.invokeArn,
});

// =============================================================================
// Deployment & Stage
// =============================================================================

const deployment = new aws.apigateway.Deployment('zephyr-deployment', {
  restApi: api.id,
  triggers: {
    redeployment: pulumi.all([
      helloMethod.id,
      helloIntegration.id,
      ingestMethod.id,
      ingestIntegration.id,
    ]).apply(ids => JSON.stringify(ids)),
  },
}, { dependsOn: [helloIntegration, ingestIntegration] });

const stage = new aws.apigateway.Stage('zephyr-stage', {
  restApi: api.id,
  deployment: deployment.id,
  stageName: 'v1',
});

// =============================================================================
// API Key & Usage Plan
// =============================================================================

const apiKey = new aws.apigateway.ApiKey('zephyr-station-key', {
  name: 'zephyr-station-01',
  description: 'API key for ESP32 weather station',
  enabled: true,
});

const usagePlan = new aws.apigateway.UsagePlan('zephyr-usage-plan', {
  name: 'zephyr-station-plan',
  description: 'Usage plan for weather station devices',
  apiStages: [{
    apiId: api.id,
    stage: stage.stageName,
  }],
  throttleSettings: {
    burstLimit: 10,
    rateLimit: 5,
  },
  quotaSettings: {
    limit: 10000,
    period: 'DAY',
  },
});

new aws.apigateway.UsagePlanKey('zephyr-usage-plan-key', {
  keyId: apiKey.id,
  keyType: 'API_KEY',
  usagePlanId: usagePlan.id,
});

// =============================================================================
// Lambda Permissions
// =============================================================================

new aws.lambda.Permission('zephyr-api-permission', {
  action: 'lambda:InvokeFunction',
  function: lambda.name,
  principal: 'apigateway.amazonaws.com',
  sourceArn: pulumi.interpolate`${api.executionArn}/*/*`,
});

// =============================================================================
// Outputs
// =============================================================================

export const helloUrl = pulumi.interpolate`https://${api.id}.execute-api.${region.name}.amazonaws.com/${stage.stageName}/hello`;
export const ingestUrl = pulumi.interpolate`https://${api.id}.execute-api.${region.name}.amazonaws.com/${stage.stageName}/ingest`;
export const apiKeyValue = apiKey.value;
export const lambdaName = lambda.name;
