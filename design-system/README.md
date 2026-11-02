# DealWaggle design system

Version 0.1.0 · Tokens, styles, components, logos and guidelines for every DealWaggle frontend.

Copy this folder into a repo, import one CSS file, and the whole app picks up DealWaggle's fonts, colours, light and dark themes, and components. Open `specimen.html` to see everything.

```
dealwaggle-design-system/
├── dealwaggle.css          ← import this one file
├── tokens/
│   ├── tokens.json         source of truth (W3C design-token format)
│   ├── tokens.css          generated CSS variables, light + dark
│   └── tailwind-theme.css  generated Tailwind v4 theme
├── css/                    fonts, base, components, mark (imported by dealwaggle.css)
├── fonts/                  Inter + Bricolage Grotesque (woff2, SIL OFL)
├── logos/                  logo, wordmark, mark, loader, app icons, manifest
├── react/                  <DWMark /> and <DWLogo /> (optional)
├── scripts/build-tokens.mjs
├── GUIDELINES.md           how to use colour, type, motion, voice, product patterns
├── CLAUDE.md               rules for AI coding agents working in the repo
└── specimen.html           visual reference
```

## Install

1. Copy the folder into the repo, for example as `design-system/`. Paths inside are relative, so any location works.
2. Import the stylesheet once, at the root of the app:

```css
/* app/globals.css (Next.js), src/index.css (Vite)… */
@import "../design-system/dealwaggle.css";
```

In Next.js you can also `import "../design-system/dealwaggle.css";` from the root layout.

3. Copy the logos the browser needs into your public folder and add the head tags:

```bash
mkdir -p public/brand && cp design-system/logos/* public/brand/
```

```html
<link rel="icon" href="/brand/mark.svg" type="image/svg+xml" />
<link rel="apple-touch-icon" href="/brand/apple-touch-icon.png" />
<link rel="manifest" href="/brand/site.webmanifest" />
<meta name="theme-color" content="#FBF8F2" media="(prefers-color-scheme: light)" />
<meta name="theme-color" content="#15120E" media="(prefers-color-scheme: dark)" />
```

4. Tell coding agents about the system: add this line to the repo's root `CLAUDE.md` (or paste the contents of `CLAUDE.md` into `AGENTS.md`):

```
@design-system/CLAUDE.md
```

### With Tailwind CSS v4

```css
@import "tailwindcss";
@import "../design-system/dealwaggle.css";
@import "../design-system/tokens/tailwind-theme.css";
```

This replaces Tailwind's default palette with DealWaggle's, so `bg-blue-500` no longer exists and off-brand colours can't slip in. You get semantic utilities that follow the theme (`bg-bg`, `bg-surface`, `text-fg`, `text-fg-muted`, `border-line`, `bg-accent`, `text-on-accent`, `text-accent-fg`, `bg-positive-soft`…), the palette (`bg-honey-500`, `text-ink-600`…), fonts (`font-display`), text styles (`text-title-1`, `text-body`…), radii, shadows and easings. The `dw-*` component classes still work alongside utilities.

### With React

```tsx
import { DWLogo, DWMark } from "../design-system/react";

<DWLogo height={28} />
<DWMark size={24} loading label="Loading" />
```

Below 48px the mark keeps the bee large; at 18px and under only the bee shows. Both components need `dealwaggle.css` loaded.

### Plain HTML

Link `dealwaggle.css` and use the `dw-*` classes. `specimen.html` has copyable markup for every component.

## Themes

Dark mode follows the operating system automatically. To force a theme, set it on `<html>`:

```html
<html data-theme="dark">   <!-- or "light"; class="dark" / class="light" also work -->
```

## What's applied globally

Importing `dealwaggle.css` sets the page background, text colour and font, link style (ink with a honey underline), focus rings, selection colour and a light reset. Everything else is opt-in through `dw-*` classes or Tailwind utilities. All of it sits in cascade layers (`theme`, `base`, `components`), so your own unlayered CSS and Tailwind utilities win when they need to.

## Changing tokens

Edit `tokens/tokens.json`, then regenerate the CSS:

```bash
node design-system/scripts/build-tokens.mjs
```

Never edit `tokens.css` or `tailwind-theme.css` by hand. When you change the system, change it here and copy the folder to the other repos so they stay identical.

## Components

`dw-btn` (primary, secondary, ghost, danger; sm, lg, icon, block) · `dw-field`, `dw-input`, `dw-select`, `dw-textarea` · `dw-card` · `dw-list` + `dw-row` (inbox rows) · `dw-badge` and `dw-status--*` · `dw-signal` (confirmed / reported / hearsay) · `dw-avatar` and `dw-avatar-stack` · `dw-internal` (internal notes) · `dw-forward` (ready-to-forward card) · `dw-alert` · `dw-toast` · `dw-empty` · `dw-nav-item` · `dw-tabs` · `dw-segmented` · `dw-kbd` · `dw-logo` · `dw-mark` (with `dw-loading`, `dw-16`, `dw-24`, `dw-32`).

## Licences

- Inter and Bricolage Grotesque: SIL Open Font License 1.1 (`fonts/OFL-*.txt`).
- Icons drawn inside `components.css` (lock, forward) come from Lucide, ISC licence.
- Everything else in this folder belongs to DealWaggle.
