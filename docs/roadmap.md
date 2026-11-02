# From foundation to launch

## First launch milestone: a trusted team inbox

The runnable foundation covers capture, reviewed facts, team/private visibility, watchlists and forward previews. The launch milestone should complete that loop with real provider accounts and identity before adding recommendation features.

1. **Accounts and organisations:** choose the identity provider; browser OIDC login/logout; invitations; email and phone verification; membership removal; organisation switching; administrator onboarding. Confirm whether users retain contributed information when leaving an organisation (current model: contributor owns their facts).
2. **Inbound pilot:** configure WhatsApp Business and Resend in test environments; provision verified channel identities; validate real sample payloads; implement PDF/deck/HTML handling with bounded downloads and storage. Agree raw-message retention and deletion behaviour.
3. **Extraction and review:** choose an LLM provider/model; implement proposals with evidence spans; review/edit/reject UI; deduplication and entity resolution; prompt-injection tests; evaluation dataset and cost limits. Decide which low-risk extractions may later auto-publish to the team.
4. **People enrichment:** choose a LinkedIn/professional-data provider and permitted data sources; map facts to evidence; distinguish public evidence from derived private context; handle freshness, conflicts and identity matches.
5. **Sharing and ownership:** external invitations and contacts; human-readable access audit; access expiry; shared organisation-owned lists; reshare permissions if needed. Current grants are read-only. Consider PostgreSQL RLS before broadening service/agent database access.
6. **Paid pilot:** set actual plans and pricing; integrate Stripe test mode end to end; harden duplicate checkout handling and reconciliation; decide seat/usage quotas; add customer support and cancellation flows.
7. **Operational launch:** PostgreSQL concurrency/load testing; browser interaction and accessibility checks; security review; backups and restore exercises; rate limiting; monitoring; retention tooling; deployment/secrets configuration. The local demo is not an internet-facing deployment.

## Follow-on product work

- In-app conversations linked to entities and shared facts, with conversation membership distinct from fact access.
- Opt-in outbound WhatsApp/email delivery, recipient selection and an exact disclosure preview; avoid automatically copying internal notes.
- Contact profiles and recipient recommendations using only authorised knowledge and explicit feedback. Recommend first; require a person to choose what leaves.
- Saved searches, reminders, enrichment freshness, portfolio/fund views and premium analytics.

## Decisions to make with the founder

- Individual and/or organisation billing; seat pricing versus usage credits; initial premium feature boundary.
- Public-data source policy and the approved people-enrichment provider.
- Organisation ownership versus contributor ownership after someone leaves a firm.
- Permission to re-share a received fact, access expiry, and whether different fields need stronger restrictions.
- Whether a future all-knowledge share should include internal notes (this version explicitly excludes them).
- Retention periods and deletion/export requirements for raw sources and derived knowledge.
