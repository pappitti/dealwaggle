export interface Fact { id: string; entity_id: string; field: string; value: string; signal: 'confirmed' | 'reported' | 'hearsay'; visibility: string; is_internal: boolean; attribution: string; channel: string; observed_at: string; owned: boolean; can_forward: boolean }
export interface Entity { id: string; name: string; kind: string; status: string; fact_count: number; summary: Fact }
export interface Detail { id: string; name: string; kind: string; assertions: Fact[] }
export interface Me { id: string; name: string; demo: boolean; organisations: { id: string; name: string; role: string }[] }
export interface Watchlist { id: string; name: string; mode: string; owned: boolean; assertions: Fact[]; grants: { id: string; user_id: string | null; organisation_id: string | null }[] }
export interface Source { id: string; body: string; channel: string; attribution: string; status: string; observed_at: string; organisation_id: string | null }
export interface TeamMember { id: string; name: string }
export interface Billing { status: string; configured: boolean; premium: boolean }
// Production OIDC integration supplies a short-lived access token in memory.
let accessToken: string | null = null;
export function setAccessToken(token: string | null) { accessToken = token; }
export async function api<T>(path: string, persona: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api${path}`, { ...options, headers: { 'Content-Type': 'application/json', 'X-Demo-User': persona, ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}), ...options.headers } });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === 'string' ? body.detail : `Couldn't save this change (${response.status}). Check the fields and try again.`);
  }
  return response.status === 204 ? undefined as T : response.json();
}
export function json(method: string, body: unknown): RequestInit { return { method, body: JSON.stringify(body) }; }
