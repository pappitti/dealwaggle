# DealWaggle design system: rules for coding agents

This repo's UI follows the DealWaggle design system in this folder. Read `GUIDELINES.md` before designing a new screen; `specimen.html` has markup for every component.

## Always

- Load styles through `dealwaggle.css` (plus `tokens/tailwind-theme.css` when the repo uses Tailwind v4). Don't copy token values into other files.
- Use semantic tokens for colour: `var(--dw-bg)`, `--dw-surface`, `--dw-text`, `--dw-text-muted`, `--dw-border`, `--dw-accent`, `--dw-accent-text`, `--dw-positive|caution|critical|info(-soft|-text)`. With Tailwind: `bg-surface`, `text-fg-muted`, `border-line`, `bg-accent`, `text-accent-fg`, etc.
- Use the spacing, radius, shadow, duration and easing tokens (`--dw-space-*`, `--dw-radius-*`, `--dw-shadow-*`, `--dw-duration-*`, `--dw-ease-*`). Spacing is a 4px grid.
- Reuse the `dw-*` component classes (or wrap them in framework components) before writing new styles: buttons, fields, cards, inbox rows, badges and statuses, signals, avatars, internal notes, forward cards, alerts, toasts, empty states, navigation, tabs.
- Use the logo files in `logos/` or the React `DWLogo` / `DWMark` components. Never redraw, recolour or retype the logo.
- Use the waggle loader (`DWMark loading`, or `.dw-mark.dw-loading`) for "DealWaggle is working" states. One per view.
- Check every screen in light and dark mode.

## Never

- Hard-coded hex colours, Tailwind default palette classes, or new font families.
- Honey (`--dw-accent`) as a text colour on light backgrounds; use `--dw-accent-text`.
- Sparkle ✨ icons or "AI magic" wording. The bee represents the product's work.
- Emoji in the interface, or Title Case labels. Use sentence case.
- Mixing internal notes and shareable content in one block. Internal = `.dw-internal`; what leaves = `.dw-forward`.
- Showing a claim without its source and signal (confirmed / reported / hearsay).

## When something is missing

If a pattern isn't covered, build it from the tokens in the same style (borders before shadows, 10px control radius, 14px card radius, Inter for UI, Bricolage Grotesque only for titles of 20px and more). Then add it to `css/components.css` and `specimen.html` here, so the design system stays the single source.
