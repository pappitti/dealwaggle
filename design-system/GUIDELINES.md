# DealWaggle design guidelines

DealWaggle helps small VC teams pass on what they hear. Someone forwards a message, the team finds what matters, and the right people get a clean note they can forward on. The design should make that loop feel effortless and trustworthy.

## Principles

1. **One action is enough.** Forwarding, sharing and finding things should take one obvious step. If a screen needs explaining, simplify it.
2. **Evidence, not assertion.** Every piece of information keeps who said it, when, and how sure we are. "Might raise next year" never looks like "raising now".
3. **Internal stays internal.** What the team says among itself and what leaves the building look different, so nobody forwards a private comment by accident.
4. **Warm, not cute.** Honey, paper and ink give the product warmth. The bee is the only playful element, and it only moves when it has something to say.
5. **The bee is the agent.** Work done by the product (reading decks, enriching companies, matching contacts) is shown with the bee. No sparkle ✨ icons, no "AI magic" language.

## Logo

| File | Use |
| --- | --- |
| `logos/logo.svg` | Default horizontal logo. Ink in light mode, paper in dark mode. |
| `logos/logo-on-light.svg`, `logos/logo-on-dark.svg` | When the background is known and fixed: emails, decks, documents. |
| `logos/wordmark.svg` | Word only, for tight horizontal spaces where the mark already appears nearby. |
| `logos/mark.svg` | The mark alone. Favicon, avatars, small spaces. It changes its own detail level when drawn at 16, 24 or 32px. |
| `logos/mark-loader.svg` | The mark dancing on a loop, for loading states. |
| `logos/app-icon.svg`, `app-icon-square.svg`, `apple-touch-icon.png` | Honey tile for app icons and home screens. |

- **Name:** write "DealWaggle" in text. The wordmark is lowercase `dealwaggle` by design; don't imitate it in copy.
- **Two-tone wordmark:** "deal" in ink (or paper on dark), "waggle" in honey. Don't swap or recolour the parts.
- **Clear space:** at least the radius of the dotted ring on every side.
- **Minimum size:** logo 20px tall; mark 16px.
- **Backgrounds:** paper, white, ink or photos with enough calm space. Never put the logo on honey; use the app icon tile instead.
- **Don't** stretch, outline, add shadows or effects, rotate, re-letter the wordmark, or add a sparkle near the bee.

## Colour

Components only use semantic tokens (`--dw-bg`, `--dw-text`, `--dw-accent`…), so light and dark switch together. The palette primitives (`--dw-honey-500`, `--dw-ink-900`…) are for charts and one-off illustration.

| Role | Light | Dark | Use |
| --- | --- | --- | --- |
| Background | paper `#FBF8F2` | `#15120E` | App canvas |
| Surface | white | `#1E1A15` | Cards, lists, inputs |
| Text | ink `#211C15` | `#F6F1E8` | Body and headings |
| Muted text | `#6B6153` | `#A99E8D` | Secondary text; 5.4:1 or better |
| Accent | honey `#F5A524` | same | Primary buttons, unread dots, the bee, selection |
| Accent text | `#92520E` | `#FBC85A` | When honey must be read as text |

- **Honey is a fill, not a text colour** on light backgrounds (it's only 2:1 on white). Use `--dw-accent-text` for honey-coloured words.
- **One honey thing per area.** A primary button, an unread dot, a selected row — not all at once.
- **Status colours mean something:** moss = positive / shared, ember = needs attention, berry = error or destructive, sky = in progress / informational. Don't use them as decoration.
- **Never rely on colour alone.** Statuses and signals always carry a word.

## Typography

Two typefaces, both self-hosted and open source (SIL OFL):

- **Bricolage Grotesque** for display and titles (20px and up) and the wordmark. It carries the brand's character.
- **Inter** for everything else: UI, lists, forms, messages.

| Style | Class / token | Size / line | Use |
| --- | --- | --- | --- |
| Display | `.dw-display` | 48/52 Bricolage 700 | Marketing, empty hero moments |
| Title 1 | `.dw-title-1` | 32/38 Bricolage 700 | Page titles |
| Title 2 | `.dw-title-2` | 24/30 Bricolage 650 | Section titles, company name on its page |
| Title 3 | `.dw-title-3` | 17/24 Inter 600 | Card and panel titles |
| Body large | `.dw-body-lg` | 16/24 Inter | Reading: forwarded messages, notes |
| Body | `.dw-body` (default) | 14/20 Inter | The app default |
| Label | `.dw-label` | 13/18 Inter 500 | Form labels, compact UI |
| Caption | `.dw-caption` | 12/16 Inter | Meta: time, source |
| Overline | `.dw-overline` | 11/16 Inter 600, caps | Small section labels |

- Sentence case everywhere, including buttons and titles.
- Numbers in lists and tables use `.dw-num` (tabular figures) so amounts line up.

## Layout and spacing

- **4px grid.** Use the spacing tokens (`--dw-space-1` = 4px … `--dw-space-20` = 80px). Most gaps are 8, 12, 16 or 24.
- **App shell:** sidebar 248px, top bar 56px, content up to 1200px; reading columns (messages, notes) up to 680px.
- **Density:** the app is a working tool. Inbox rows are about 64px; controls are 36px (28px compact, 44px on touch).
- **Radii:** 10px for controls, 14px for cards, 20px for modals. People are circles; companies and funds are rounded squares.
- **Elevation:** surfaces are separated by borders first. Shadows are for things that float: menus, popovers, toasts, modals.

## Motion

| Token | Value | Use |
| --- | --- | --- |
| `--dw-duration-fast` | 140ms | Hover, press |
| `--dw-duration-base` | 220ms | Popovers, panels, toasts |
| `--dw-duration-slow` | 360ms | Large surfaces |
| `--dw-ease-standard` | cubic-bezier(.2,0,0,1) | Default |
| `--dw-ease-buzz` | slight overshoot | Rare moments of delight: a share confirmed, a toast landing |

**The waggle dance** is the brand's motion. Use it to mean "DealWaggle is working on it":

- Show the loader when a wait is likely to pass ~400ms; under that, show nothing.
- One dancing bee per view. Several loaders at once becomes noise; use skeletons for the rest.
- The logo in the navigation may dance on hover. Elsewhere, the mark stays still unless something is loading.
- Reduced motion is respected automatically: the bee pulses gently instead of dancing, and UI transitions drop to 0ms.

## Product patterns

### Capture acknowledgement
When someone forwards something, answer within seconds, then work in the background.
> Got it. Reading the deck now — it'll be in your inbox in a minute.

### Evidence and signal
Every fact shows where it came from: **who · how · when**, e.g. `via Claire Martin · WhatsApp · 12 Oct`. Claims carry a signal:

| Signal | Class | Means |
| --- | --- | --- |
| ● Confirmed | `.dw-signal--confirmed` | Said by the company, or in a document they sent |
| ◐ Reported | `.dw-signal--reported` | From a named source |
| ○ Hearsay | `.dw-signal--hearsay` | Unsourced, second-hand or speculative |

Keep tense honest: "Raising €4m (reported)" is different from "May raise next year (hearsay)". Newer evidence doesn't erase older evidence; show the latest and keep the history.

### Internal vs shareable
- **Internal notes** (`.dw-internal`): dashed border, faint hatching, "Internal" label with a lock. Team comments, opinions, owners.
- **Forward card** (`.dw-forward`): white card with a honey edge, "Ready to forward" label. It shows exactly the text that will leave, nothing more.
- Never mix the two in one block. When drafting a forward, internal notes are never copied in automatically; flag anything that looks private before it goes.

### Forwardable messages
Recipients should get value without installing anything. Messages are plain text that survives WhatsApp and email:

```
*Acme Robotics* is raising a €4m seed — looking for a lead.
Warehouse picking robots; €600k ARR, 3 paying customers.
Founder: Lea Dubois (ex-Exotec). Deck attached.
Source: a former colleague of hers, 12 Oct.
Interested? I can make the intro.
```

- Company in bold on the first line, then what they want.
- Two or three facts, each with a number when possible.
- Say where it came from and when.
- End with one clear ask.
- No emoji, no hype, no internal comments. A "via DealWaggle" signature is optional and off by default.

### Opportunity statuses
| Status | Class | Colour |
| --- | --- | --- |
| New | `.dw-status--new` | honey |
| Reviewing | `.dw-status--reviewing` | sky |
| Shared | `.dw-status--shared` | moss |
| On hold | `.dw-status--on-hold` | ember |
| Passed | `.dw-status--passed` | outline only |

### Numbers and dates
- Money: `€4m`, `$12.5m`, `€600k`. Lowercase k/m, no space, currency first.
- Rounds: Pre-seed, Seed, Series A, Series B… (capitalised as written).
- Dates: relative under a week (`2h`, `Yesterday`, `Tue`), then `12 Oct`, then `12 Oct 2025` for other years.

## Voice and tone

DealWaggle sounds like a sharp colleague who is good at passing things on: brief, specific, never breathless.

| Instead of | Write |
| --- | --- |
| Our AI magically enriched this deal! ✨ | Added 6 details from the deck and the company website. |
| Oops! Something went wrong. | Couldn't read the deck. Forward it again or upload the PDF. |
| Successfully shared! | Sent to Marc. |
| Are you sure you want to delete? | Delete this note? It can't be recovered. |
| Leverage your network synergies | Share with the 3 investors who back B2B robotics |

- Write to one person, in sentence case, in the active voice.
- Put the useful part first. Cut adverbs.
- Name people and companies; avoid "user", "entity", "item".
- No emoji in the interface. Exclamation marks are almost never needed.

## Accessibility

- Body and muted text are at least 4.5:1 on every background; input borders at least 3:1.
- Every interactive element has a visible focus ring (`--dw-focus`).
- Touch targets are 44px; use `.dw-btn--lg` on mobile.
- Statuses, signals and errors pair colour with text and shape.
- The mark has an accessible name; pass `label=""` (React) or `aria-hidden="true"` when it sits next to visible text.

## Icons

Use [Lucide](https://lucide.dev) (ISC licence) at 16, 18 or 20px with the default 2px stroke and `currentColor`. Its rounded line style matches the mark. Don't mix icon sets.
