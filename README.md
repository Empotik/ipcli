# Prompt Engine

A lightweight, **class‑based CLI prompt framework** that supersedes the old monolithic `interactive_prompt()` helper. It preserves drop‑in compatibility while giving you smaller, test‑friendly building blocks for richer terminal UIs.

## Why another prompt helper?

| Pain in the old code                                                           | How Prompt Engine fixes it                                                                                                                |
| ------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------- |
| Flag explosion (`multi_select`, `multi_entry_freeform`, `display_as_menu`, …). | **Specialised classes**: `OptionPrompt`, `FreeformPrompt`, `YesNoPrompt`. Flags shrink to `multi`, `display`, `allow_custom`, `freeform`. |
| Hard to extend / unit‑test.                                                    | Pure methods and protected hooks (`_render_prompt`, `_parse_input`)—just subclass to add pagination, validators, etc.                     |
| Recursive re‑prompt risked deep call‑stacks.                                   | Iterative retry loop in `PromptBase`.                                                                                                     |
| Yes/No boilerplate dict every time.                                            | Dedicated **`YesNoPrompt`** (and wrapper shortcut).                                                                                       |
| No explicit one‑line free‑form mode.                                           | `freeform="single"` or `FreeformPrompt(multi=False)`.                                                                                     |

## Quick‑start

### 1 · Keep your old calls (facade)

```python
from prompt_engine import interactive_prompt

lang = interactive_prompt(
    "Preferred language?",
    options=["Python", "Rust", "Go"],
    default="Python",
)
```

### 2 · Use the OO API for new code

```python
from prompt_engine import OptionPrompt, FreeformPrompt, YesNoPrompt

# single‑choice list
fruit = OptionPrompt(
    "Favourite fruit?",
    options=["Apple", "Banana", "Cherry"],
    default="Banana",
).ask()

# multi‑select with custom entries
langs = OptionPrompt(
    "Languages spoken?",
    options={"🇬🇧 English": "en", "🇯🇵 Japanese": "ja"},
    multi=True,
    allow_custom=True,
).ask()

# single free‑form
name = FreeformPrompt("What is your name?").ask()

# yes / no shortcut
confirmed = YesNoPrompt("Delete all recordings?", default="no").ask()
```

## API surface

| Class / Function       | Purpose                                                  |
| ---------------------- | -------------------------------------------------------- |
| `interactive_prompt()` | Back‑compat façade that routes to the right prompt type. |
| `PromptBase`           | Abstract foundation (retry loop, confirmation dialog).   |
| `OptionPrompt`         | Single / multi selection from list or dict.              |
| `FreeformPrompt`       | Single line or multi‑line free‑form text collection.     |
| `YesNoPrompt`          | Boolean convenience wrapper around `OptionPrompt`.       |

Key arguments (OO & facade share names):

- `options` – list/dict of choices, or `None` for free‑form.
- `multi` – enable comma‑separated multi‑select.
- `allow_custom` – accept tokens not in `options`.
- `display="inline" | "menu"` – numbered list vs compact A/B/C.
- `freeform="none|single|multi"` – explicit free‑form mode for the facade.
- `confirm=True` – ask once more before returning.

## Version history

| Version                           | Date       | Highlights                                                                                                                                                                |
| --------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **0.1 “Ancient”**                 |            | Single giant `interactive_prompt()` with many flags.                                                                                                                      |
| **0.2 “Old helper”**              |            | Split into helpers (`normalize_options`, `display_menu`…), but same API.                                                                                                  |
| **0.3 “Prompt Engine”** (current) | 2025‑05‑25 | • Class hierarchy<br>• Back‑compat wrapper<br>• Explicit single vs multi free‑form<br>• Dedicated `YesNoPrompt`.<br>• Iterative retry loop.<br>• Inline prompt bug‑fixes. |

## Roadmap / future work

- **Pagination** for long option lists (>40 items).
- **Validator / caster hooks** (`int`, `Path`, regex, etc.).
- **Timeout / non‑interactive default** for CI pipelines.
- **Theming hooks** to integrate with richer TUI frameworks.
- **Unit‑test suite** (pytest) + GitHub CI workflow.

Contributions & suggestions welcome—open an issue or drop a PR!
