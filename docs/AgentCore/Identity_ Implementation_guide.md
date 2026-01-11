### Developer's Guide to AgentCore Identity: Implementation and Best Practices

#### 1.0 Introduction to AgentCore Identity

##### 1.1 Understanding the Strategic Role of Identity for AI Agents

Amazon Bedrock AgentCore Identity is a specialized identity and credential management service engineered for AI agents and automated workloads. For developers, its strategic importance lies in its ability to provide a secure, scalable, and compliant foundation for agentic applications. By enabling agents to access resources on behalf of users while maintaining strict security controls, AgentCore Identity removes significant complexity from the development process and allows teams to focus on building intelligent, high-value applications. It provides a robust framework for authentication, authorization, and credential management, ensuring that as agents become more autonomous, they operate within clearly defined, auditable security boundaries.The core capabilities of AgentCore Identity are designed to address the unique challenges of agent-based systems:

* **Secure Credential Management:**  The service abstracts away the complexities of credential handling. Through the AgentCore SDK, it automatically retrieves and injects credentials like OAuth tokens and API keys into agent code using simple annotations. This reduces boilerplate code and minimizes the risk of exposing sensitive secrets within the application.  
* **Agent Identity and Access Controls:**  AgentCore Identity supports a sophisticated impersonation flow, allowing agents to perform actions on behalf of users. Every action is tied to a specific agent and user identity, which creates a clear and comprehensive audit trail for security and compliance purposes.  
* **Broad Identity Provider (IdP) Compatibility:**  The service integrates seamlessly with existing enterprise identity providers, including Amazon Cognito, Okta, Microsoft Azure Entra ID, and Auth0. This eliminates the need for user migration or rebuilding established authentication flows, allowing developers to leverage existing identity infrastructure securely.To facilitate a clear understanding, the following table defines key terminology used throughout this guide.| Term | Definition || \------ | \------ || **Workload Identity** | A specialized identity type used to represent an AI agent or automated workload. || **OAuth 2.0 authorizer** | An SDK component that authenticates and authorizes incoming OAuth 2.0 API requests to agent endpoints. It validates tokens before allowing access to agent services. || **OAuth 2.0 client credentials grant (2LO)** | OAuth client credentials grant used for machine-to-machine authentication where no user interaction is required. Agents use 2LO to authenticate themselves directly with resource servers. || **OAuth 2.0 authorization code grant (3LO)** | OAuth authorization code grant that involves user consent and interaction. Agents use 3LO when they need explicit user permission to access user-specific data from external services like Google Calendar or Salesforce. |

Mastering the implementation of AgentCore Identity begins with understanding its high-level workflow, which is the next critical step for developers.

##### 1.2 Key Use Cases

AgentCore Identity is engineered for complex, real-world scenarios that demand robust security and sophisticated identity management. It provides foundational capabilities for building enterprise-grade agents that can operate safely and effectively across diverse environments.

###### *Enterprise Automation Scenarios*

Enterprise workflows frequently span multiple trust domains, operating across both cloud-native and on-premises systems. This creates a significant challenge for maintaining consistent security and propagating user identity. AgentCore Identity addresses this by providing a centralized credential management solution that works across these hybrid environments. It supports both AWS IAM-based authentication for internal resources and OAuth 2.0 or API key authentication for external enterprise systems, enabling agents to operate seamlessly while adhering to consistent security standards.

###### *Development and DevOps Scenarios*

Agents used in development and DevOps pipelines often require elevated privileges to manage infrastructure and deploy applications, presenting a unique security risk. AgentCore Identity mitigates this challenge through fine-grained, role-based access controls and comprehensive audit logging. It allows developers to configure policies that limit an agent's access to specific environments (e.g., development vs. production), repositories, or deployment targets based on its identity. This ensures that powerful automation tasks are performed securely and all actions are auditable for compliance.These use cases are enabled by a well-defined authentication and authorization workflow that ensures secure, auditable access to resources.

#### 2.0 The AgentCore Identity Workflow: A Conceptual Overview

##### 2.1 The End-to-End Authentication and Authorization Flow

Before configuring specific components, it is essential for developers to understand the end-to-end identity workflow. This conceptual overview breaks down the sequence of operations an agent performs to securely obtain credentials and access a third-party service on behalf of a user. The following steps detail the user-delegated authentication flow, often referred to as a 3-Legged OAuth (3LO) grant, which requires explicit user consent.

1. **Invoke Agent & Request Authorization**  The user interacts with an application, which invokes an AI agent to perform a task. The agent determines it needs access to a third-party resource (e.g., Google Drive) and requests an authorization URL from AgentCore Identity via the AgentCore SDK.  
2. **Generate and Return Authorization URL**  AgentCore Identity communicates with the third-party Authorization Server to generate a unique authorization URL and a session URI. It returns this URL to the agent, which then passes it back through the application to the user's browser.  
3. **User Authorization and Token Acquisition**  The user is directed to the authorization URL, where they sign in to the third-party service and grant the agent consent to access their data. Upon successful consent, the authorization server redirects the user to a pre-configured callback endpoint managed by the application. The application's backend validates the user's active session to prevent session fixation attacks and then instructs AgentCore Identity, which then communicates directly with the Authorization Server's token endpoint to securely exchange the code for an access token. The token is then securely stored in the AgentCore Identity token vault.  
4. **Re-invoke Agent to Access Resource**  The application re-invokes the agent to continue the original task. The agent now requests the stored access token from AgentCore Identity. With the token in hand, the agent can make authorized API calls to the resource server (e.g., Google Drive) to access the user's data and complete the task.The practical implementation of this secure and auditable flow begins with the initial setup of credential providers for external resources.

#### 3.0 Initial Setup: Configuring Outbound Credential Providers

##### 3.1 Establishing Secure Connections to External Resources

Credential providers are the foundational components that enable AI agents to securely access external, third-party resources. They act as a centralized and secure configuration point for storing the client IDs, secrets, and endpoint information required for authentication protocols like OAuth 2.0 or for direct API key access. This section provides step-by-step instructions for configuring the two primary types of providers.

###### *Configuring an OAuth Client*

OAuth clients are used to connect agents with external services that support the OAuth 2.0 protocol, enabling both machine-to-machine (2LO) and user-delegated (3LO) authorization flows.To add an OAuth client using a custom provider via the console:

1. Open the AgentCore Identity console.  
2. In the  **Outbound Auth**  section, choose  **Add OAuth client / API key** , then choose  **Add OAuth client** .  
3. Enter a unique  **Name**  for your OAuth client.  
4. For  **Provider** , select  **Custom** .  
5. Configure the  **Authorization server details** , either by providing an OpenID Connect discovery URL for automatic configuration or by manually entering the issuer, authorize endpoint, and token endpoint URLs.  
6. Enter the  **Client ID**  and  **Client Secret**  obtained from the third-party service.  
7. Choose  **Save changes** .

###### *Configuring an API Key*

API keys are used for services that require a static, key-based authentication token. AgentCore Identity securely stores these keys, allowing agents to retrieve and use them without embedding the secret directly in their code.To add an API key via the console:

1. Open the AgentCore Identity console.  
2. In the  **Outbound Auth**  section, choose  **Add OAuth client / API key** , then choose  **Add API key** .  
3. Enter a unique  **Name**  for your API key configuration.  
4. Enter the  **API key**  value.  
5. Choose  **Add API key** .Once credential providers are configured, the next step is to create and manage the identities of the agents that will use them.

#### 4.0 Managing Agent Identities

##### 4.1 Creating and Organizing Workload Identities

A "workload identity" is the core digital representation of an agent within the AgentCore Identity service. It serves as the principal to which permissions are granted and against which actions are audited. Managing these identities is crucial for applying fine-grained access controls, ensuring accountability, and maintaining a clear security posture for your entire agent ecosystem.Agent identities can be created through two primary methods, offering flexibility for different deployment scenarios.

###### *Automatic Creation by Runtime and Gateway*

For streamlined deployments, workload identities are created automatically when an agent is deployed via AgentCore Runtime or AgentCore Gateway. This integration ensures that every deployed agent is immediately provisioned with a unique identity. The Amazon Resource Name (ARN) of the workload identity is returned in the deployment response, allowing developers to immediately use it in IAM policies for access control.

###### *Manual Creation*

For scenarios requiring more direct control or integration with custom deployment pipelines, identities can be created manually using the AWS Command Line Interface (CLI) or AWS SDKs. This approach is ideal for developers who need to script identity creation as part of a broader infrastructure-as-code setup or for testing purposes.All workload identities, whether created automatically or manually, are managed within the  **Agent identity directory** , which provides a centralized console for viewing and managing agent identities.With agent identities established, the next critical step is to secure the agent endpoints these identities are associated with.

#### 5.0 Securing Agent Endpoints with Inbound Authorization

##### 5.1 Protecting Your Agent from Unauthorized Access

While outbound authorization enables an agent to securely access external services, inbound authorization is equally critical—it controls who can access and invoke the agent itself. This security layer acts as the front door to your agent, ensuring that only authenticated and authorized callers can interact with it. AgentCore Identity integrates with AgentCore Runtime to protect agent endpoints using Inbound JWT (JSON Web Token) authorization. This allows you to leverage industry-standard OAuth 2.0 and OpenID Connect protocols to secure your agent runtime.To configure an Inbound Authorizer for your agent runtime, follow these steps:

1. Open the AgentCore Identity console.  
2. In the  **Inbound Auth**  section of the navigation pane, choose  **Authorizers** .  
3. Choose  **Configure authorizer** .  
4. Provide a unique  **Name**  for your authorizer.  
5. Configure the OAuth settings to match your identity provider's configuration.  
6. Choose  **Save Changes** .The configuration requires you to define several key OAuth 2.0 parameters, which are used to validate incoming JWT bearer tokens:  
* **Discovery URL:**  The OpenID Connect discovery endpoint of your identity provider (e.g., https://your-idp.com/.well-known/openid-configuration). This URL allows AgentCore Identity to automatically fetch the necessary public keys and endpoint information.  
* **Allowed Audiences:**  A list of valid audience (aud) values that incoming JWTs must contain. This ensures the token was intended for your agent.  
* **Allowed Clients:**  A list of client identifiers (client\_id or cid) that are permitted to access the agent.  
* **Allowed Scopes:**  A list of permitted scope values (scope claim) required for the agent to process a request.  
* **Required Custom Claims:**  A list of custom claims that must be present in the JWT for it to be considered valid, enabling fine-grained, attribute-based access control.With the agent endpoint secured against unauthorized access, the focus now shifts to the agent's code, where it will programmatically retrieve credentials for external services.

#### 6.0 Implementing Outbound Authentication in Agent Code

##### 6.1 Programmatically Obtaining and Using Credentials

This section provides developers with the practical, code-level patterns for programmatically obtaining credentials managed by AgentCore Identity. The AgentCore SDK dramatically simplifies this process by abstracting away the underlying complexity of token management and retrieval, allowing you to focus on your agent's core logic.

###### *Simplified Access with SDK Decorators*

The most direct way to inject an OAuth 2.0 access token into an agent function is by using the @requires\_access\_token decorator. This declarative approach instructs the SDK to handle the entire credential retrieval process automatically. The SDK will check for a valid cached token or initiate the appropriate OAuth flow to obtain one before executing the decorated function.The following example demonstrates how to apply this decorator to a function that needs to access Google Drive:  
\# Injects Google Access Token  
@requires\_access\_token(  
    \# Uses the same credential provider name created above  
    provider\_name="google-provider",  
    \# Requires Google OAuth2 scope to access Google Drive  
    scopes=\["https://www.googleapis.com/auth/drive.metadata.readonly"\],  
    \# Sets to OAuth 2.0 Authorization Code flow  
    auth\_flow="USER\_FEDERATION",  
    \# Prints authorization URL to console  
    on\_auth\_url=lambda x: print("\\nPlease copy and paste this URL in your browser:\\n" \+  x),  
    \# If false, caches obtained access token  
    force\_authentication=False,  
    \# The callback URL for handling session binding  
    callback\_url='oauth2\_callback\_url\_for\_session\_binding',  
)  
async def read\_from\_google\_drive(\*, access\_token: str):  
    print(access\_token)  \# You can see the access\_token  
    \# Make API calls...

###### *Implementing the 3-Legged OAuth (3LO) User Consent Flow*

For user-delegated access (3LO), where the agent must act on behalf of a user, the application must present an authorization URL to the user to obtain their consent. The SDK facilitates this by providing the URL via the on\_auth\_url callback. Two common patterns for handling this in a production application are:

* **Streaming response pattern:**  For applications that support streaming, the authorization URL can be sent immediately as part of the response stream, allowing the user interface to react in real-time.  
* **Polling pattern:**  The application backend stores the authorization URL and its pending status. The frontend client polls an endpoint to retrieve the URL once it becomes available.

###### *Securing 3LO with OAuth 2.0 Authorization URL Session Binding*

Session binding is a critical security measure that prevents session fixation attacks by ensuring the user who grants consent at the identity provider is the same user who initiated the request in your application. This is especially vital for AI agents, as their autonomous nature makes them a prime target; without this binding, a malicious actor could trick an agent into using a session they initiated to access a victim's resources. This is achieved by binding the authorization flow to the user's active application session.To implement this security control, follow these four steps:

1. **Create an Application Callback URL:**  Host a new URL in your user-facing application that is accessible from the user's browser. This endpoint will receive the redirect from the identity provider and must be able to access the user's current, active session data (e.g., from a cookie or browser storage).  
2. **Add the Callback URL to the Credential Provider:**  In the AgentCore Identity console, add the URL from Step 1 to the list of allowed callback URLs for your OAuth 2.0 credential provider.  
3. **Use the Callback URL in the SDK:**  When calling the SDK to get the authorization URL (e.g., via the @requires\_access\_token decorator), provide this callback URL in the callback\_url parameter.  
4. **Implement the Callback Handler:**  In your application's callback handler (from Step 1), you must verify that the user has an active, valid session. Then, call the CompleteResourceTokenAuth API, presenting the original user identifier (e.g., user ID or JWT from the active session) and the session URI received in the redirect. This final step proves the user's identity and allows AgentCore Identity to securely fetch and store the access token.A successful implementation must be paired with strong security and operational discipline, which the next section will cover in detail.

#### 7.0 Security and Operational Best Practices

##### 7.1 Ensuring Robust and Compliant Identity Management

Secure and effective identity management extends beyond the initial configuration and code implementation. Adhering to established best practices is essential for protecting data, maintaining compliance, and operating a robust agentic ecosystem. This section outlines key principles and recommendations for the ongoing governance of AgentCore Identity.

###### *Adhere to the Shared Responsibility Model*

While AWS is responsible for securing the underlying cloud infrastructure of AgentCore Identity, the customer is responsible for the security of their application. This includes implementing secure coding practices, validating all inputs to prevent prompt injection attacks, and properly configuring IAM policies to protect resources.

###### *Encrypt Data at Rest with Customer-Managed Keys*

By default, all data stored in AgentCore Identity, such as credentials in the token vault, is encrypted at rest with an AWS-owned key. For organizations requiring greater control and auditability over encryption, it is a best practice to specify a customer-managed AWS KMS key. This allows you to manage the key's lifecycle and access policies directly.

###### *Apply the Least-Privilege Principle*

Always create and apply identity-based policies that grant only the permissions necessary for an agent or user to perform their specific tasks. Avoid overly permissive policies. This principle minimizes the potential impact of a compromised agent or credential.

###### *Utilize Resource Tagging*

Apply tags to your AgentCore Identity resources, such as workload identities and credential providers. Tags are key-value pairs that serve two primary purposes:

1. **Cost Allocation:**  Use tags like CostCenter or Project to track and allocate AWS costs accurately.  
2. **Attribute-Based Access Control (ABAC):**  Use tags in the Condition element of your IAM policies to create fine-grained permissions. For example, you can grant access to a resource only if its Environment tag is production.

###### *Partition User IDs from Multiple Providers*

This is a critical security practice when integrating with multiple identity providers. To prevent a user from one IdP from impersonating a user who happens to have the same user ID in a different IdP, you must partition the user IDs. A recommended pattern is provider\_id+user\_id (e.g., cognito+user123 and auth0+user123). Failure to do so could result in a user from one provider inadvertently or maliciously gaining access to the data and permissions of a completely different user from another provider. This ensures that user identities are globally unique across your entire system.With these best practices in mind, the following section provides reference material for integrating with specific third-party providers.

#### 8.0 Reference: Integrating with Third-Party Providers

##### 8.1 Configuration Details for Popular Identity Services

This section serves as a practical reference guide, providing the specific configuration parameters needed to set up various popular services as outbound resource providers in AgentCore Identity. The following JSON structures can be used as a template when creating credential providers via the AWS CLI or SDKs.

##### 8.1.1 Auth0 by Okta

Auth0 can be configured as an identity provider for both inbound authorization to your agent and outbound resource access. To configure Auth0 for outbound access, first create an application in the Auth0 portal to obtain a Client ID and Client Secret.  
{  
  "name": "Auth0",  
  "credentialProviderVendor": "CustomOauth2",  
  "oauth2ProviderConfigInput": {  
    "customOAuth2ProviderConfig": {  
      "oauthDiscovery": {  
        "discoveryUrl": "https://your-domain.auth0.com/.well-known/openid-configuration"  
      },  
      "clientId": "your-client-id",  
      "clientSecret": "your-client-secret"  
    }  
  }  
}

##### 8.1.2 CyberArk

To configure CyberArk as an outbound resource provider, use the following configuration. Replace the placeholder values with the tenant ID, Client ID, and Client Secret from your CyberArk application setup.  
{  
  "name": "CyberArk",  
  "credentialProviderVendor": "CyberArkOauth2",  
  "oauth2ProviderConfigInput": {  
    "includedOauth2ProviderConfig": {  
      "clientId": "your-client-id",  
      "clientSecret": "your-client-secret",  
      "authorizeEndpoint": "https://your-tenant-id.id.cyberark.cloud/OAuth2/Authorize/\_\_idaptive\_cybr\_user\_oidc",  
      "tokenEndpoint": "https://your-tenant-id.id.cyberark.cloud/OAuth2/Token/\_\_idaptive\_cybr\_user\_oidc",  
      "issuer": "https://your-tenant-id.id.cyberark.cloud/\_\_idaptive\_cybr\_user\_oidc"  
    }  
  }  
}

##### 8.1.3 Okta

To configure Okta as an outbound resource provider, use the following configuration. Replace the placeholder values with your Okta tenant, authorization server, Client ID, and Client Secret.  
{  
  "name": "Okta",  
  "credentialProviderVendor": "OktaOauth2",  
  "oauth2ProviderConfigInput": {  
    "includedOauth2ProviderConfig": {  
      "clientId": "your-client-id",  
      "clientSecret": "your-client-secret",  
      "authorizeEndpoint": "https://your-tenant.okta.com/oauth2/your-authorization-server/v1/authorize",  
      "tokenEndpoint": "https://your-tenant.okta.com/oauth2/your-authorization-server/v1/token",  
      "issuer": "https://your-tenant.okta.com/oauth2/your-authorization-server"  
    }  
  }  
}

##### 8.1.4 Salesforce

To integrate with Salesforce, first set up a Connected App in the Salesforce developer portal to obtain the Client ID and Client Secret required for the OAuth client configuration.  
{  
  "name": "Salesforce",  
  "credentialProviderVendor": "SalesforceOauth2",  
  "oauth2ProviderConfigInput": {  
    "includedOauth2ProviderConfig": {  
      "clientId": "your-client-id-from-connected-app",  
      "clientSecret": "your-client-secret-from-connected-app"  
    }  
  }  
}

##### 8.1.5 Slack

To integrate with Slack, create a Slack application in the Slack API portal. From the "OAuth & Permissions" section, obtain the Client ID and Client Secret needed to configure the OAuth client.  
{  
  "name": "Slack",  
  "credentialProviderVendor": "SlackOauth2",  
  "oauth2ProviderConfigInput": {  
    "includedOauth2ProviderConfig": {  
      "clientId": "your-client-id-from-slack-app",  
      "clientSecret": "your-client-secret-from-slack-app"  
    }  
  }  
}

##### 8.1.6 Zoom

To configure Zoom as an outbound resource provider, use the following configuration. The Client ID and Client Secret must be obtained by creating an OAuth app in the Zoom App Marketplace.  
{  
  "name": "Zoom",  
  "credentialProviderVendor": "ZoomOauth2",  
  "oauth2ProviderConfigInput": {  
    "includedOauth2ProviderConfig": {  
      "clientId": "your-client-id",  
      "clientSecret": "your-client-secret"  
    }  
  }  
}

Moving from configuration to operations, the final section of this guide covers essential monitoring and observability practices.

#### 9.0 Observability and Monitoring

##### 9.1 Tracking the Performance and Health of Identity Operations

Effective observability is crucial for maintaining the health, security, and performance of your agent's identity operations. Proactive monitoring helps you identify performance bottlenecks, troubleshoot authentication failures, and ensure that your agents are operating reliably. AgentCore Identity provides detailed metrics and tracing capabilities to give you deep visibility into its operations.

###### *Enabling Tracing*

Tracing allows you to track the flow of requests through AgentCore Identity, providing a detailed, step-by-step view of each operation. This is invaluable for debugging complex authentication flows and identifying latency issues.To configure tracing for Identity resources using the console:

1. Open the AgentCore Identity page in the AgentCore console.  
2. In the Identity pane, select the OAuth client or API key for which you want to enable tracing.  
3. In the  **Tracing**  pane, choose  **Edit** , toggle the widget to  **Enable** , and then choose  **Save** .

###### *Key CloudWatch Metrics*

AgentCore Identity automatically emits detailed performance and usage metrics to Amazon CloudWatch. These metrics provide quantitative insights into the success, failure, and throttling rates of credential retrieval operations. Monitoring these metrics is essential for understanding the operational health of your identity integration.The following table summarizes key resource access metrics:| Metric Name | Description || \------ | \------ || ResourceAccessTokenFetchSuccess | Tracks successful OAuth2 token fetch operations from credential providers. || ResourceAccessTokenFetchFailures | Tracks failed OAuth2 token fetch operations by exception type. || ResourceAccessTokenFetchThrottles | Tracks throttled OAuth2 token fetch operations. || ApiKeyFetchSuccess | Tracks successful API key fetch operations from credential providers. || ApiKeyFetchFailures | Tracks failed API key fetch operations by exception type. || ApiKeyFetchThrottles | Tracks throttled API key fetch operations. |

###### *Enhancing Tracing with Custom Headers*

To improve end-to-end observability, developers can include optional headers in their API calls to AgentCore Identity. These headers help correlate traces and logs across multiple services.The most important header for distributed tracing is X-Amzn-Trace-Id. By propagating this header through your application stack, you can link an agent's request to the subsequent identity operations and downstream service calls, creating a unified trace in services like AWS X-Ray.By following this guide, developers can effectively implement, secure, and monitor AgentCore Identity to build sophisticated, secure, and trustworthy AI agents.  
