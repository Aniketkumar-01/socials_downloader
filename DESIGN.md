---
name: OmniDownloader
description: Universal Video & Playlist Downloader - Sleek Obsidian & Cyber-Refined Console
colors:
  primary: "#00f0b5"
  primary-hover: "#00d9a3"
  primary-dim: "rgba(0, 240, 181, 0.12)"
  secondary: "#00d2ff"
  secondary-dim: "rgba(0, 210, 255, 0.12)"
  canvas-bg: "#080a0f"
  shell-bg: "#0e121a"
  surface-bg: "#131822"
  surface-elevated: "#18202c"
  surface-hover: "#1e2736"
  input-bg: "#0b0e15"
  text-primary: "#f8fafc"
  text-secondary: "#94a3b8"
  text-tertiary: "#64748b"
  status-success: "#10b981"
  status-warning: "#f59e0b"
  status-error: "#f43f5e"
  border-subtle: "rgba(255, 255, 255, 0.07)"
  border-medium: "rgba(255, 255, 255, 0.12)"
  border-strong: "rgba(255, 255, 255, 0.2)"
  border-focus: "rgba(0, 240, 181, 0.55)"
typography:
  display:
    fontFamily: "Outfit, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 700
    lineHeight: 1.35
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "Outfit, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"
    fontSize: "1.15rem"
    fontWeight: 700
    lineHeight: 1.4
    letterSpacing: "-0.02em"
  title:
    fontFamily: "Outfit, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"
    fontSize: "0.98rem"
    fontWeight: 600
    lineHeight: 1.45
    letterSpacing: "normal"
  body:
    fontFamily: "Outfit, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"
    fontSize: "0.88rem"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  label:
    fontFamily: "Outfit, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"
    fontSize: "0.76rem"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "0.04em"
  mono-telemetry:
    fontFamily: "JetBrains Mono, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace"
    fontSize: "0.8rem"
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: "normal"
rounded:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "18px"
  xl: "24px"
  full: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "#051410"
    rounded: "{rounded.md}"
    padding: "0.72rem 1.6rem"
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
  button-secondary:
    backgroundColor: "{colors.surface-elevated}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.md}"
    padding: "0.65rem 1.15rem"
  input-console:
    backgroundColor: "{colors.input-bg}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.lg}"
    padding: "0.35rem 0.45rem 0.35rem 1rem"
---

# Design System: OmniDownloader

## Overview

**Creative North Star: "The Cyber-Refined Media Terminal"**

OmniDownloader's visual system embodies high-cadence local media extraction: instantaneous, disciplined, and razor-sharp. Rejecting generic AI neon gradients, floating colored orbs, and fragmented card-in-card layouts, the interface operates as a unified obsidian console where ingestion, inspection, and telemetry coexist in a single view.

The experience prioritizes operator velocity. Visual authority comes from disciplined obsidian tonal depth, surgical 1px micro-borders, and deliberate luminescent cyber-teal (`#00f0b5`) accents that perform strictly functional work: active states, focus rings, progress gauges, and primary triggers.

**Key Characteristics:**
- **Obsidian Tonal Architecture**: Deep monochromatic ground (`#080a0f`) elevating into disciplined slabs (`#0e121a`, `#131822`, `#18202c`) using ambient depth instead of costume drop shadows.
- **Functional Luminescence**: Cyber-teal (`#00f0b5`) and electric cyan (`#00d2ff`) strictly reserved for active states, data telemetry, and download actions.
- **Precision Telemetry**: Tabular numeric readouts set in `JetBrains Mono` ensuring stable, non-jumping layout during multi-megabyte/second streaming.
- **Unified Action Hub**: Form ingestion and media inspection flow in a singular viewport without modals or multi-step wizards.

## Colors

The palette is anchored in deep cool obsidian tones, with functional luminescent accents doing explicit work.

### Primary
- **Cyber-Teal** (`#00f0b5`): The primary action and completion color. Used for "Download Now", "Fetch Info", progress indicators, active tags, and focus rings.

### Secondary
- **Electric Cyan** (`#00d2ff`): Secondary technical accent. Used for platform identification badges, gradient progress fills, and documentation links.

### Tertiary
- **Amethyst Violet** (`#a855f7`): Reserved for multi-item playlist indicators and batch counters.

### Neutral
- **Obsidian Canvas** (`#080a0f`): Deep background canvas.
- **Console Shell** (`#0e121a`): Primary container ground for command deck, inspection bay, and telemetry.
- **Surface Layer** (`#131822`): Elevated sub-surfaces, toolbars, and tray containers.
- **Surface Hover** (`#1e2736`): Interactive hover feedback ground.
- **Text Primary** (`#f8fafc`): High-contrast clean white for headings and primary labels.
- **Text Secondary** (`#94a3b8`): Slate tinted text for metadata, creator channels, and helper text.
- **Text Tertiary** (`#64748b`): Muted slate for placeholders, shortcut pills, and hints (≥4.5:1 contrast maintained).

### Named Rules
**The Rarity Rule.** Luminescent cyber-teal covers ≤8% of any rendered viewport. Its high contrast against obsidian draws immediate focus to the primary task.

**The No-Gradient-Text Rule.** Text emphasis is conveyed purely through font weight, scale, and color hierarchy; gradient-clipped text is prohibited.

## Typography

**Display Font:** Outfit (fallback: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif)  
**Body Font:** Outfit (fallback: sans-serif)  
**Label/Mono Font:** JetBrains Mono (ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace)

**Character:** Modern geometric sans-serif with crisp letterforms paired with tabular monospace numerals for live download telemetry.

### Hierarchy
- **Headline** (700, 1.25rem, line-height 1.35, -0.02em tracking): Media title and major section anchors.
- **Title** (600, 0.98rem, line-height 1.45): Ingestion labels, playlist tray headers, and utility names.
- **Body** (400, 0.88rem, line-height 1.5): Descriptive copy, instructions, and error descriptions.
- **Label** (600/700, 0.74rem–0.78rem, letter-spacing 0.04em, uppercase): Quality dock labels, platform tags, and status badges.
- **Telemetry Mono** (500/700, 0.8rem–1.25rem): Real-time speed (MB/s), ETA timer, engine versions, and percentage gauges.

## Layout

A centered single-column command console (`max-width: 920px`) with a tight 1.25rem vertical rhythm. Components stack seamlessly without nested card fatigue. The layout remains fluid down to 360px mobile viewports (adjusting grid inspection to single-column) and comfortable on desktop displays up to 4K.

## Elevation & Depth

Depth is achieved through ambient tonal layering (`#080a0f` $\to$ `#0e121a` $\to$ `#131822` $\to$ `#18202c`) bounded by 1px subtle micro-borders (`rgba(255, 255, 255, 0.07)`).

### Shadow Vocabulary
- **Shell Elevation** (`box-shadow: 0 20px 48px -12px rgba(0, 0, 0, 0.7), 0 0 0 1px rgba(255, 255, 255, 0.07)`): Applied to command deck and inspection bay.
- **Dock Elevation** (`box-shadow: 0 8px 24px -6px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.07)`): Applied to top header bar and toasts.

### Named Rules
**The Soft Depth Rule.** Hard zero-blur offset shadows are banned. Depth must always be ambient, soft, and restrained.

## Shapes

- **Corner Language**: Subtle, gradual radii scaling with component size:
  - Hotkey pills & badges: 4px (`--radius-xs`)
  - Platform pills & secondary buttons: 8px–12px (`--radius-sm` to `--radius-md`)
  - Input bays: 18px (`--radius-lg`)
  - Console decks & stages: 24px (`--radius-xl`)
  - Status indicators & pill tags: 9999px (`--radius-full`)
- **Borders**: Uniform 1px hairline strokes with variable alpha opacity. Thick left/right colored accent borders are strictly banned.

## Components

### Ingestion Bay
- **Shape**: Rounded capsule (`18px` radius).
- **Background**: Deep obsidian input field (`#0b0e15`) with `rgba(255, 255, 255, 0.12)` border.
- **Focus**: Border shifts to cyber-teal (`rgba(0, 240, 181, 0.55)`) with a subtle 3px glow ring (`rgba(0, 240, 181, 0.12)`).
- **Embedded Controls**: Clear trigger, paste dock with `Ctrl+V` keycap indicator, and primary "Fetch Info" trigger.

### Primary Action Button
- **Shape**: 12px radius.
- **Color**: Cyber-teal (`#00f0b5`) with `#051410` high-contrast dark text.
- **Hover/Active**: Lifts by -1px with soft cyber-teal glow (`rgba(0, 240, 181, 0.25)`). Returns to 0 on active click.

### Platform Indicators
- **Shape**: Full pill (`9999px`).
- **State**: Dim slate (`rgba(255, 255, 255, 0.04)`) at rest; automatically lights up with cyan/teal glow when a matching platform link is pasted.

### Telemetry Gauge
- **Shape**: Pill track (`8px` height) with smooth CSS linear fill transition.
- **Colors**: Cyan-to-teal linear gradient with live tabular percentage numerals.

## Do's and Don'ts

### Do:
- **Do** preserve 100% of authentic original titles and filename sanitization.
- **Do** format live numeric readouts in `JetBrains Mono` to prevent layout jitter during download progress.
- **Do** ensure focus rings and selection colors are themed consistently to `#00f0b5`.
- **Do** keep download action paths single-click (paste $\to$ download $\to$ open in Windows Explorer).

### Don't:
- **Don't** use gradient text or decorative background neon blur blobs.
- **Don't** use unicode glyphs or emoji as icons (`🍪`, `✕`, `?`); use authored SVG vector paths.
- **Don't** nest cards inside cards.
- **Don't** use hard offset drop shadows (`4px 4px 0`).
