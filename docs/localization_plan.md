# Localization Plan

This document defines how Quantum Minesweeper will add localization without
forking the server and browser products or allowing translated presentation to
leak into game state. It is an implementation guide, not a second task-status
list: `roadmap.md` remains the only authority on priority and completion.

## Initial product decision

The first supported locales are:

| Locale | Display name | Role |
| --- | --- | --- |
| `en` | English | Default locale and complete fallback |
| `sv` | Svenska | Supported translation |
| `it` | Italiano | Supported translation |

Locale selection follows this precedence:

1. An explicit saved preference.
2. The browser's preferred languages.
3. English.

An explicit choice persists across visits. Automatic detection is not itself
stored as an explicit preference, so a user who has never chosen a language can
still follow a later browser-language change. The selector should offer an
"Automatic" choice that clears the saved preference, in addition to English,
Svenska, and Italiano.

Regional language tags normalize to their supported base locale. For example,
`sv-SE` resolves to `sv`, `it-CH` resolves to `it`, and unsupported tags resolve
to English after all browser preferences have been considered. Locale matching
is case-insensitive and accepts both hyphens and underscores at its input
boundaries.

## Scope and boundaries

Localization is presentation. It must not change the rules, saved-game schema,
command syntax, analytics vocabulary, or simulator interfaces.

The following values remain stable and untranslated:

- serialized game-state field names and status values;
- form values such as `identify`, `clear`, `sandbox`, and move-set keys;
- command tokens such as `M`, `P`, `H`, `CX`, and `CZ`;
- `WinCondition`, `MoveSet`, and `QuantumGate` enum names;
- analytics column names and stored enum values;
- snapshot keys and version identifiers;
- mathematical notation, qubit labels, and gate symbols where they are used as
  notation rather than prose.

Only labels describing these values are translated. A Swedish player may see a
translated label for Clear, for example, while the submitted value remains
`clear` and analytics continue to store `CLEAR`.

The initial implementation is deliberately divided into vertical passes. A
pass must work in both server and browser/PWA modes before the next presentation
surface is added. The TUI is included only after the shared web product is
complete because it has its own Rich-based interaction and lifecycle.

## Content model

Use a hybrid model: short interface messages live in JSON catalogs; substantial
educational content remains in separate Markdown or HTML files.

### Short interface strings

Store catalogs under:

```text
src/qminesweeper/i18n/
  en.json
  sv.json
  it.json
```

English is the source catalog and the runtime fallback. Catalog keys describe
meaning rather than copying the English text:

```json
{
  "meta.locale_name": "English",
  "header.online_players": "Online players: {count}",
  "header.open_tutorial": "Open tutorial",
  "header.about": "About Quantum Minesweeper",
  "header.toggle_help": "Toggle help",
  "header.toggle_theme": "Toggle theme",
  "setup.title": "Game Setup",
  "setup.board_size": "Board size",
  "setup.start_game": "Start Game",
  "board.cell_position": "Row {row}, column {column}"
}
```

Use flat dotted keys. They are easy to compare across catalogs, easy to address
from Jinja and JavaScript, and avoid language-specific object structures.

Catalog requirements:

- All supported catalogs have exactly the same message keys as English.
- Placeholders are named, never positional.
- Every translation has the same placeholder set as its English source.
- User-provided or computed values are interpolated as text, never as HTML.
- Markup remains in templates or DOM construction. Catalog values are plain
  text except for narrowly reviewed cases that explicitly require safe markup.
- Translators may reorder named placeholders to follow natural grammar.
- Keys are stable API. Editing English wording does not require renaming a key.
- Obsolete keys are removed from every catalog in the same change.

The initial translator needs simple named interpolation. Before translating
messages with grammatical number, add a shared plural contract rather than
constructing sentences from fragments. Browser plural selection should use
`Intl.PluralRules`; Python must implement the same catalog shape and categories.
Do not assume that an English singular/plural pair is sufficient for future
locales.

### Long-form content

Store localized user documentation by locale:

```text
src/qminesweeper/docs/
  en/
    simple_setup.md
    advanced_setup.md
    about.md
  sv/
    simple_setup.md
    advanced_setup.md
    about.md
  it/
    simple_setup.md
    advanced_setup.md
    about.md
```

Store contextual help with the same topic identifiers in each locale:

```text
src/qminesweeper/static/help/
  en/
    H-gate/
      text.html
      visual.html
    mine-counter/
      text.html
      visual.html
  sv/
    H-gate/
      text.html
      visual.html
  it/
    H-gate/
      text.html
      visual.html
```

Topic identifiers and filenames remain language-independent because JavaScript
uses them as lookup keys. Each translated topic preserves the semantic content,
equations, links, and accessibility information of its English source.

Visuals that contain no natural-language text remain shared assets. A visual
containing labels such as "control" and "target" is localized, or is refactored
so shared geometry and translated labels are separate. Do not duplicate images
or SVG geometry merely to change surrounding prose.

Long-form fallback is per document or help topic. If a localized file is absent,
the loader uses the English file with the same identifier. Missing translations
must also be reported by validation so fallback does not quietly become the
permanent state of a nominally complete locale.

## Shared Python localization layer

Add `src/qminesweeper/i18n.py` as the framework-free owner of locale and catalog
rules. It should have no FastAPI dependency so the static builder and tests can
reuse it.

Its responsibilities are:

- declare `DEFAULT_LOCALE = "en"` and `SUPPORTED_LOCALES = ("en", "sv", "it")`;
- normalize external language tags;
- choose the first supported language from an ordered preference list;
- load and cache JSON catalogs from package resources;
- translate a key with named values and English fallback;
- fail clearly in development validation when keys or placeholders are invalid;
- resolve localized document paths with English fallback;
- expose all catalogs to the browser build without maintaining a second list.

Suggested pure functions are:

```python
normalize_locale(tag: str | None) -> str | None
detect_locale(preferences: Iterable[str]) -> str
load_catalog(locale: str) -> Mapping[str, str]
translate(locale: str, key: str, **values: object) -> str
localized_document(root: Path, locale: str, relative_path: str) -> Path
```

Runtime fallback should protect users, but programming mistakes should remain
visible. The recommended behavior is:

- unsupported locale input resolves through detection and ultimately English;
- missing non-English message uses the English message and logs a warning;
- a missing English key returns a conspicuous key marker in production and
  fails catalog validation in tests/builds;
- missing or extra interpolation values raise during tests and builds;
- no request may mutate the cached catalog mappings.

## Server locale resolution and persistence

The server must resolve locale independently for every request. Never store a
mutable current locale in a module global, Jinja global, or shared
`ProductConfig`: concurrent requests may use different languages.

Use a dedicated preference cookie, for example `qms_locale`. It contains only a
validated locale code and uses:

- `Path=/` so setup, game, About, and `/app/` share it;
- `SameSite=Lax`;
- `Secure` when the request scheme is HTTPS;
- a long but finite maximum age;
- no `HttpOnly`, because the shared browser selector must keep the PWA and
  server preference aligned.

For an ordinary server request, resolve:

1. Valid `qms_locale` cookie.
2. Ordered `Accept-Language` entries, respecting quality values.
3. English.

Add a small locale-change endpoint for progressive enhancement. A POST receives
either `auto` or one supported locale and a local return path. It sets or clears
the cookie, then redirects to the validated same-origin path. Reject absolute,
scheme-relative, and malformed return targets so the endpoint cannot become an
open redirect.

Each template response receives a request-specific context containing:

```text
locale          active normalized locale
locale_mode     "explicit" or "automatic"
t               translator bound to that locale
docs            documents loaded for that locale
```

A shared context helper should add these values to all visible server pages.
Do not update each route with ad hoc locale logic. Administrative pages may
initially remain English, but they still need a correct `<html lang>` value and
must not break the shared header selector.

Setup validation errors currently originate as English Python exception text.
Do not translate arbitrary exception strings. A later error-localization pass
should map stable validation error codes to presentation messages while keeping
diagnostic details in logs.

## Browser/PWA locale resolution and persistence

The static browser build has no request headers or server-side template render
at visit time. Add a small browser localization module loaded before UI code
that creates dynamic labels.

Use the same storage key as the cookie name: `qms_locale`. Resolve:

1. Valid explicit value in `localStorage`.
2. `navigator.languages` in order, then `navigator.language`.
3. English.

Storage can fail in private or restricted environments. Reads and writes must be
guarded, and failed storage must leave the current session usable. An explicit
choice should take effect for the current page even if persistence fails.

The language selector behavior is:

- selecting English, Svenska, or Italiano stores that locale in `localStorage`;
- on a server origin, it also updates `qms_locale` for server pages;
- selecting Automatic removes both saved values;
- the active locale updates `<html lang>`;
- changing language updates presentation without resetting or reconstructing
  the game;
- a reload may be used in the first pass where it simplifies replacing
  server-rendered long-form content, provided the current browser game remains
  restorable from its existing snapshot mechanism.

The JavaScript API should remain small:

```javascript
QMSI18n.locale()
QMSI18n.t(key, values)
QMSI18n.setPreference(localeOrAuto)
QMSI18n.apply(root)
```

Mark static template text with `data-i18n` attributes. Use explicit attributes
for accessibility and metadata, such as `data-i18n-title` and
`data-i18n-aria-label`, rather than parsing or matching rendered English text.
Dynamic renderer code calls `t()` directly.

Catalog loading must not make offline language switching unreliable. The static
build copies all catalogs and all supported first-pass documents into the
bundle, includes them in the content fingerprint, and adds them to the service
worker's install-time core list. A player who installed the app while online
must be able to switch among all supported languages while offline.

Avoid a visible English-to-translated flash. The initial page should determine
its locale before showing localized content, then reveal the page after the
catalog and selected document are ready. Failure reveals the complete English
page rather than leaving the interface hidden.

## Language selector design

Place one selector in the shared header so it is available from setup, game,
About, server mode, and browser mode. It must remain usable at narrow mobile
widths and must not make the header depend on a fixed height.

The options use autonyms so they remain recognizable in every active locale:

```text
Automatic
English
Svenska
Italiano
```

The label for Automatic is translated because its meaning depends on the active
interface language. The language autonyms stay fixed. The control needs a
translated accessible name such as "Language" and an indication when the
current locale came from automatic detection.

Use a native `<select>` in the first pass. It gives keyboard, touch, and screen
reader behavior without a custom popup implementation. Style it through the
existing theme tokens; do not add literal colors outside the designated theme
blocks.

## Template and page integration

Convert visible template strings incrementally while preserving shared Jinja
templates as the source of page structure.

The first pass covers:

- `<html lang>` and shared metadata needed by setup;
- the header language selector and header action labels;
- the shared Help and About overlay controls;
- the footer's accessible labels and session label;
- simple and advanced setup headings, labels, options, and actions;
- survey text shown on setup;
- the browser runtime loading panel;
- the localized `simple_setup.md` document.

Every translated element should still render readable English without
JavaScript. Server pages receive translated text from Jinja. Static browser HTML
is built with complete English fallback, then the browser localization module
applies the detected or saved locale.

Page titles and descriptions are translated where the whole visible page is
translated. Canonical URLs remain locale-neutral in the first pass because
locale is a preference, not a URL namespace. Do not add `hreflang` until there
are stable, crawlable locale-specific URLs.

## Localized document loading

Extend `docs_render.py` without making templates aware of filesystem paths.
The loader should accept a locale and return the same document-key mapping it
returns today. For each key it selects the requested locale file or English
fallback, then runs the existing Markdown and MathJax-compatible rendering.

The server loads documents for the active request locale. It must not expose one
startup-global `DOCS` mapping if pages can use different locales. Catalog and
rendered-document contents may be cached by `(locale, document)` because source
files are immutable during a deployed process.

The browser build renders localized Markdown to HTML at build time. It emits
language-specific document fragments under a predictable static path, for
example:

```text
dist/static/docs/en/simple_setup.html
dist/static/docs/sv/simple_setup.html
dist/static/docs/it/simple_setup.html
```

The browser localization module replaces only the designated document host. It
must not replace the setup form or attach duplicate setup event handlers.

When migrating the current flat English documents into `docs/en/`, update all
loaders, packaging tests, static-build inputs, and documentation references in
the same change. Do not retain two editable English copies.

## Contextual help migration

Move the contextual help only after locale selection is stable. Migrate all
English topics to `static/help/en/` first, then add Swedish and Italian using
the same topic tree.

Update `help.js` so a topic request follows:

1. Fetch the active locale's `text.html` and `visual.html`.
2. If either localized component is missing, fetch its English counterpart.
3. Rewrite static asset paths exactly as the current server/browser abstraction
   requires.
4. Cache results by `(locale, topic)` rather than topic alone.
5. Refresh the open topic when the locale changes.

A help topic is a semantic unit. Validation should compare the locale directory
trees, parse every HTML and SVG fragment, verify referenced assets, and report
which components are falling back. Equations and quantum terminology require
human review; a syntactically complete catalog is not sufficient scientific QA.

## Dynamic game UI migration

After the first pass, localize strings generated in:

- `render.js`: status labels, tool labels, actions, outcomes, probe results,
  cell accessibility names, and tooltips;
- `tools.js`: armed-tool and region-selection hints;
- `help.js`: help state, missing-topic messages, and toggle labels;
- `browser-main.js`: loading stages, setup failures, restore prompts, and
  browser-only notices;
- `about.js`: load failures and direct-open fallback;
- `engine.js`: user-facing request failure fallback.

Keep symbols and visible labels separate. A button may display `H` while its
translated accessible name explains "Hadamard gate." Never derive a command
token from translated text or a button's visible label; use existing data
attributes and canonical tokens.

When a locale changes during a game, re-render presentation from the existing
serialized state. Do not issue a move, recreate the board, reset probe regions,
change the selected tool, or write analytics merely because text changed.

Number formatting should eventually use locale-aware browser and Python
formatters, but numeric precision is part of the game presentation contract.
Localization may change decimal separators only after server and browser output
remain consistent and tests cover copying/readability of clue values. The first
pass should retain the existing invariant numeric formatting.

## About, admin, TUI, and manuscript

The About page is long-form content and follows the localized Markdown model.
Its surrounding actions and offline-install text use catalog messages.

Administrative pages can remain English during the player-facing rollout. When
localized, operational identifiers, setting values, database columns, and CSV
headers should stay canonical unless an export format is deliberately versioned.
Only their displayed labels should change.

The TUI requires a separate pass after web completion. It should reuse Python
catalogs and locale normalization but may use an environment variable or command
line option in addition to process locale detection. Rich markup stays outside
translated strings where practical, and command tokens remain canonical.

The manuscript remains canonical English scientific prose and is not part of
the application localization bundle. Localization must nevertheless preserve
its terminology and mathematical meaning. Translation review should use the
implemented rules and canonical paper terms for mine probability, expectation
clues, Clear mode, pinning, and the two distinct entanglement observables.

## Validation and test strategy

### Catalog tests

Add tests that:

- load every supported catalog;
- assert exact key parity with English;
- assert string values and valid UTF-8;
- compare named placeholders for every key;
- reject unknown locale declarations;
- exercise missing-key and English-fallback behavior;
- verify catalogs are included in the built wheel.

### Locale-resolution tests

Cover:

- no preference and no language header gives English;
- `sv-SE,sv;q=0.9,en;q=0.8` gives Swedish;
- `it-CH` gives Italian;
- an unsupported first choice falls through to a later supported choice;
- an explicit cookie overrides browser headers;
- malformed and unsupported cookie values are ignored;
- Automatic clears the explicit preference;
- cookie attributes and redirect validation are correct;
- concurrent requests can render different locales without leakage.

### Document tests

Cover:

- each declared document exists in English;
- Swedish and Italian coverage is reported;
- a missing localized document falls back as a whole to English;
- Markdown renders equations and headings as before;
- generated HTML does not include an accidental duplicate title;
- the static build emits each supported locale's document fragment.

### Browser tests

Use small Node/jsdom checks for:

- `localStorage` preference precedence;
- `navigator.languages` detection;
- storage failure fallback;
- selector changes and Automatic reset;
- `<html lang>` updates;
- text and accessibility-attribute replacement;
- placeholder interpolation;
- changing locale without changing serialized state or selected tools;
- localized document replacement without duplicate event listeners.

Perform a live smoke test in both server and static browser modes at desktop and
mobile widths. Check English, Swedish, and Italian, including long labels,
keyboard navigation, screen-reader names, theme switching, setup submission,
starting a game, reload persistence, and offline switching in an installed PWA.

### Build and release gates

Localization changes touch package data, templates, static JavaScript, and the
browser bundle. Run:

```text
pixi run check
pixi run release-check
```

Also inspect the built wheel and browser distribution for all catalogs and
localized documents. Confirm the service-worker fingerprint changes when any
translation changes and that all first-pass locale resources are available
offline before declaring browser support complete.

## Implementation sequence

### Pass A: localization foundation and setup vertical slice

Introduce the framework-free Python locale module, three short-string catalogs,
catalog validation, request-scoped server context, browser locale module,
shared selector, persistence, `<html lang>`, setup/shell translations, and the
three localized `simple_setup.md` files. Update the static builder and service
worker so this complete slice works offline.

This pass is complete when a user can arrive with Swedish or Italian browser
preferences, see the translated setup experience, explicitly switch language,
reload with the preference retained, return to Automatic, start a game with
unchanged canonical parameters, and do all of this in both server and PWA modes.

### Pass B: dynamic game presentation

Translate the renderer, tools, game actions, outcome messages, probe UI,
accessibility labels, and browser runtime messages. Ensure locale changes
re-render the current game without mutation.

This pass is complete when all ordinary gameplay text and accessibility names
are translated in all three locales and no translated value enters commands,
state, snapshots, or analytics.

### Pass C: full long-form content and contextual help

Translate About, advanced setup documentation, and every contextual help topic.
Implement topic-level fallback, locale-aware help caching, directory parity
validation, and scientific review.

This pass is complete when validation reports no English fallback in Swedish or
Italian player-facing content, except content explicitly designated as shared
notation or artwork.

### Pass D: secondary surfaces

Decide and implement the desired coverage for admin pages and the TUI. Add
locale-aware SEO URLs only if discoverable translated pages are a product goal.
Keep CSV, analytics, commands, and operational identifiers canonical.

### Pass E: documentation and release synchronization

Update `architecture.md` with the stable localization boundaries once they are
implemented. Update `roadmap.md` in the same changes that add, complete, remove,
or redefine localization work. Update README, user documentation, contextual
help, and `CHANGELOG.md` to describe only behavior that actually ships.

## Translation workflow

English changes are source changes, not merely copy edits. A change to an
English key or long-form document should identify the Swedish and Italian files
that need review. Automated checks establish structural completeness; a fluent
reviewer establishes linguistic quality.

For each translated change:

1. Confirm the English source is correct and consistent with implemented rules.
2. Update Swedish and Italian translations using the same message keys or file
   paths.
3. Run catalog and document parity checks.
4. Review rendered text in context, including narrow layouts.
5. Review mathematical notation, gate terminology, and accessibility wording.
6. Record intentional English fallback explicitly until it is translated.

Do not translate generated output by hand. Translate source catalogs and source
documents, then rebuild browser/package artifacts through the normal tasks.

## Decisions to preserve during implementation

- English is always complete and is the final fallback.
- An explicit preference wins over automatic detection.
- Automatic mode remains available and does not become an implicit saved locale.
- Localization is request-scoped on the server and session-safe in the browser.
- Server and browser consume the same source catalogs and localized documents.
- Templates continue to own page structure; `render.js` remains the only game
  renderer.
- Game state stays presentation-free.
- Internal identifiers and persisted data are never translated.
- Long prose stays in Markdown/HTML files rather than JSON strings.
- Offline PWA users can access every supported locale.
- Missing translations fall back safely but remain visible to validation.
- No language rollout is called complete without linguistic, scientific,
  accessibility, responsive-layout, server, and offline-browser review.
