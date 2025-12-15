# Privacy Policy

**Last updated**: December 15, 2025

## Overview

code/chef respects your privacy. This policy explains what data we collect and how we use it.

## Data Collection

code/chef **does not collect any personal data** by default. The extension operates locally in your VS Code environment.

### Local Operation

When used without an API key:

- ✅ All processing happens on your machine
- ✅ No data is sent to external servers
- ✅ No telemetry or analytics collected
- ✅ Complete privacy

### Optional Cloud Orchestrator

If you configure an API key to use the cloud orchestrator:

**What we collect:**

- **Request logs**: Timestamp, agent used, workflow type (retained 7 days for debugging)
- **Token usage metrics**: Count of tokens used per request (for future billing)
- **Error logs**: Stack traces when errors occur (retained 7 days)

**What we DO NOT collect:**

- ❌ Your source code (never stored on our servers)
- ❌ File contents or file names
- ❌ Personal information (name, email, etc.)
- ❌ VS Code telemetry or usage patterns
- ❌ Third-party service credentials

**Data Retention:**

- Request logs: 7 days
- Error logs: 7 days
- Token usage: 90 days (for billing when paid plans launch)
- No long-term storage of code or personal data

### Self-Hosted Option

For complete data privacy, self-host the orchestrator:

- Full control over all data
- No external API calls
- Deploy on your own infrastructure
- See [DEPLOYMENT.md](https://github.com/Appsmithery/code-chef/blob/main/support/docs/getting-started/DEPLOYMENT.md)

## Third-Party Services

When using the cloud orchestrator, your requests may be processed by:

### LLM Providers

- **OpenRouter** (models: Claude, GPT-4, Qwen, DeepSeek, Gemini)
  - Privacy policy: https://openrouter.ai/privacy
  - Data: Prompts and responses (not stored long-term)
- **Gradient AI** (model training via AutoTrain)
  - Privacy policy: https://gradient.ai/privacy
  - Data: Training datasets only (when using ModelOps)

### Vector Database

- **Qdrant Cloud** (semantic code search)
  - Privacy policy: https://qdrant.tech/legal/privacy-policy/
  - Data: Code embeddings only (no source code text)

### Observability (Optional)

- **LangSmith** (tracing and debugging)
  - Privacy policy: https://smith.langchain.com/privacy
  - Data: Traces opt-in only (disabled by default)
  - You can disable: Set `LANGCHAIN_TRACING_V2=false`

## Cookies and Tracking

code/chef does not use:

- ❌ Cookies
- ❌ Browser tracking
- ❌ Analytics (Google Analytics, etc.)
- ❌ Advertising pixels

## Data Security

### In Transit

- All API requests use HTTPS (TLS 1.3)
- API keys transmitted securely
- No plaintext transmission of sensitive data

### At Rest

- API keys stored in VS Code's secure credential storage
- Logs encrypted at rest (AES-256)
- Database backups encrypted

### Access Control

- API keys required for orchestrator access
- Rate limiting per API key (1000 req/day during beta)
- Automatic key rotation on breach detection

## Your Rights

### Access Your Data

Request a copy of your data: Email alex@appsmithery.co

### Delete Your Data

Request deletion of all logs: Email alex@appsmithery.co

### Opt-Out

Stop using the cloud orchestrator at any time:

- Remove API key from settings
- Extension continues to work locally
- Or self-host the orchestrator

## Children's Privacy

code/chef is not directed at children under 13. We do not knowingly collect data from children.

## Changes to This Policy

We'll notify users of material changes:

- GitHub release notes
- Email to beta users
- 30 days notice before changes take effect

## International Users

### Data Location

- Cloud orchestrator hosted in USA (DigitalOcean NYC datacenter)
- Vector database hosted in USA (Qdrant Cloud)
- LLM providers: USA and international (OpenRouter)

### GDPR Compliance

For EU users:

- Data minimization: We collect only what's necessary
- Right to access: Email alex@appsmithery.co
- Right to deletion: Email alex@appsmithery.co
- Right to portability: Export available on request

## Contact

Privacy questions or concerns?

**Email**: alex@appsmithery.co  
**GitHub**: [github.com/Appsmithery/code-chef/issues](https://github.com/Appsmithery/code-chef/issues)

**Mailing Address**:  
Appsmithery LLC  
[Address available on request]

## Open Source

code/chef is open source (MIT License):

- Review the code: [github.com/Appsmithery/code-chef](https://github.com/Appsmithery/code-chef)
- Audit security: All source code available
- Self-host: Complete control over your data
