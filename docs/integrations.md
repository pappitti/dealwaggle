# Integrations and worker operations

## Provider endpoints

| Provider | Endpoint | Verification | Processing |
| --- | --- | --- | --- |
| WhatsApp Business Cloud API | `GET /webhooks/whatsapp` | Verify token challenge | Setup handshake only |
| WhatsApp Business Cloud API | `POST /webhooks/whatsapp` | `X-Hub-Signature-256` HMAC over raw body | Message ID dedupe, verified phone → user/team, text source |
| Resend | `POST /webhooks/resend` | Svix ID/timestamp/signature over raw body | `email.received`, forwarding address → user/team, fetch full text |
| Stripe | `POST /webhooks/stripe` | Stripe signature with timestamp tolerance | Subscription/checkout events → authoritative subscription refresh |

Configure HTTPS URLs and signing secrets before pointing live providers here. Missing configuration returns 503; invalid signatures return 401 (403 for a failed Meta challenge). Webhooks are capped at 1 MiB and do not trust client-supplied user or organisation IDs. Failed persistence does not acknowledge delivery as successful.

### WhatsApp

Set the Meta app secret, an independent challenge verify token and the expected business phone-number ID. Only the configured business number is accepted for ingestion. A `channel_identities` row maps a **previously verified** sender phone (digits in provider format) to a user and active organisation membership.

There is intentionally no endpoint that accepts an unverified phone and claims ownership. The onboarding verification flow is a launch requirement. For controlled integration testing, provision the row using an administrative script/session after verifying the phone outside this build. Unlinked senders and unsupported media are retained in blocked jobs and never assigned to a guessed account.

Text messages are supported. Attachments, decks, voice notes, delivery receipts, opt-in management, template messages and outbound API sends are not yet implemented. Forwarded contact attribution is reviewed by the user: the immediate sender is not assumed to be the original source.

### Resend

Subscribe to `email.received` and configure the Svix signing secret. Receiving webhooks contain metadata; the worker uses the Resend API key to retrieve plain text from the fixed `https://api.resend.com/emails/receiving/{email_id}` endpoint. It never fetches an arbitrary URL supplied in a message.

For each user, provision a high-entropy receiving address and its `channel_identities` row (`channel=email`, lowercase full recipient address, verified user/team). Treat forwarding aliases as routing capabilities; possession of an alias is not verified authorship. Do not infer an account from a spoofable From header. Sender verification, alias rotation, rate limits and receiving-domain configuration are onboarding work.

HTML-only messages and attachments block for review; they are not silently treated as empty content. Do not log provider API responses containing private messages.

### Stripe

Use test-mode keys during integration. Configure one Stripe price ID for the first organisation plan and enable the billing portal. The backend sets the price and quantity; the browser cannot supply arbitrary prices or customer IDs. No prices or plan economics were assumed in this foundation.

Subscribe to `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`, and `checkout.session.completed`. Sync is queued durably and uses the provider's current customer subscriptions, not event arrival order. Customer IDs must already belong to an organisation in DealWaggle. Unknown customers cannot grant access.

Before launch, test checkout completion/cancellation, payment failures, expired/incomplete subscriptions, upgrades, proration, taxes, customer deletion, repeated checkout attempts and subscription reconciliation in the Stripe test environment. Seat-based pricing and usage quotas are not implemented.

## Worker operation

```sh
uv run dealwaggle-worker             # poll continuously
uv run dealwaggle-worker --once      # process at most one available job
uv run dealwaggle-worker --retry JOB_UUID
```

Only failed or blocked jobs can be explicitly retried. Inspect the cause first: retrying an unconfigured provider will block again. The `jobs` table contains status, attempts, next availability and a safe error code/class. The `webhook_events` table retains the authenticated event for troubleshooting and replay. Access to both tables must be restricted; their payloads may contain private information.

A review UI for operators, retention/purge tooling, provider reconciliation and queue metrics are still required. Do not keep raw messages indefinitely by accident; agree a retention policy before accepting real customer data.

## References checked during implementation

- [Meta WhatsApp webhook verification](https://whatsapp.github.io/WhatsApp-Nodejs-SDK/api-reference/webhooks/start/)
- [Resend inbound email](https://resend.com/features/inbound)
- [Resend webhook verification examples](https://github.com/resend/resend-skills/blob/main/skills/agent-email-inbox/references/webhook-setup.md)
- [Stripe webhook handling](https://docs.stripe.com/webhooks)
- [SQLAlchemy locking/select API](https://docs.sqlalchemy.org/en/20/core/selectable.html#sqlalchemy.sql.expression.Select.with_for_update)
- [FastAPI JWT authentication](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
