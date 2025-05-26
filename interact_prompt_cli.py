from __future__ import annotations

"""Prompt‑Engine
=================
A compact, extendable framework that replaces the old
`interactive_prompt` helper with a tiny class hierarchy and a
back‑compat façade.

Usage examples
--------------
```py
from prompt_engine import interactive_prompt, YesNoPrompt

# Convenience façade (keeps old call‑sites working)
fruit = interactive_prompt(
    "Favourite fruit?",
    options=["Apple", "Banana", "Cherry"],
    default="Banana",
)

# Direct class use for finer control
confirmed = YesNoPrompt("Delete all recordings?", default="no").ask()
```"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence, Union

from catalyst import shared

plim = shared.plim  # colour / prompt helper

__all__ = [
    "PromptBase",
    "OptionPrompt",
    "FreeformPrompt",
    "YesNoPrompt",
    "interactive_prompt",
]

# ──────────────────────────────────────────────────────────────────────────────
# Foundation
# ──────────────────────────────────────────────────────────────────────────────

@dataclass(kw_only=True)
class PromptBase:
    """Abstract base class for every interactive prompt."""

    prompt: str
    retries: int = 3
    confirm: bool = False

    # internal state
    _attempts: int = field(init=False, default=0)

    # public -----------------------------------------------------------------
    def ask(self):
        """Interactively asks until valid or retries exhausted."""
        while self._attempts < self.retries:
            value = self._do_ask()
            if value is _Retry:
                self._attempts += 1
                continue
            if self.confirm and not self._confirm(value):
                self._attempts += 1
                continue
            return value
        plim.error("❌ Too many invalid attempts.")
        plim.divider()
        return None

    # internals --------------------------------------------------------------
    def _do_ask(self):
        raise NotImplementedError

    # helper -----------------------------------------------------------------
    def _confirm(self, value):
        display = ", ".join(value) if isinstance(value, Sequence) and not isinstance(value, str) else value
        resp = plim.ask(f"⚠️ Confirm selection:\n{display}\nConfirm? [Y/n]")
        return (resp or "").strip().lower() not in {"n", "no"}


class _Retry:  # sentinel used to restart the prompt loop
    pass

# ──────────────────────────────────────────────────────────────────────────────
# Option selection prompt
# ──────────────────────────────────────────────────────────────────────────────

@dataclass(kw_only=True)
class OptionPrompt(PromptBase):
    """Single‑ or multi‑choice selection from a predefined set of options."""

    options: Union[Sequence[str], Dict[str, Any]]
    default: Union[str, int, List[Union[str, int]], None] = None
    case_sensitive: bool = False
    multi: bool = False
    allow_custom: bool = False
    display: str = "inline"  # "inline" | "menu"

    # computed ---------------------------------------------------------------
    _option_dict: Dict[str, Any] = field(init=False)
    _display_keys: List[str] = field(init=False)
    _value_map: Dict[str, Any] = field(init=False)
    _index_map: Dict[str, Any] = field(init=False)

    # life‑cycle -------------------------------------------------------------
    def __post_init__(self):
        # normalise option container -----------------------------------------
        if isinstance(self.options, dict):
            self._option_dict = self.options
        else:
            self._option_dict = {opt: opt for opt in self.options}

        self._display_keys = list(self._option_dict.keys())
        self._build_maps()
        self._default_keys = self._resolve_default_keys(self.default)

    # ------------------------------------------------------------------------
    def _do_ask(self):
        prompt_msg = self._render_prompt()
        raw = plim.ask(prompt_msg) or ""
        if raw == "":
            return self._handle_empty()
        return self._parse_input(raw)

    # rendering --------------------------------------------------------------
    def _render_prompt(self):
        if self.display == "menu":
            for idx, key in enumerate(self._display_keys, 1):
                tag = " [default]" if key in self._default_keys else ""
                text = f" [{idx}] {key}{tag}"
                (plim.bold if key in self._default_keys else plim.plain)(text)
            rng = f"1-{len(self._display_keys)}"
            if self.multi:
                suffix = f" [{rng} / all / none{' / custom' if self.allow_custom else ''}]"
            else:
                suffix = f" [{rng}{' / custom' if self.allow_custom else ''}]"
            return f"{self.prompt}{suffix}: "
        # inline
        opts_repr = "/".join(self._display_keys)
        if self.multi:
            opts_repr = f"{opts_repr}/all/none"
        hint = " | custom" if self.allow_custom else ""
        default_txt = f" (default: {', '.join(self._default_keys)})" if self._default_keys else ""
        return f"{self.prompt} [{opts_repr}{hint}]{default_txt}: "

    # helpers ----------------------------------------------------------------
    def _handle_empty(self):
        if self.default is None:
            return None if not self.multi else []
        return self._option_dict[self._default_keys[0]] if not self.multi else [
            self._option_dict[k] for k in self._default_keys
        ]

    def _parse_input(self, raw: str):
        norm = raw if self.case_sensitive else raw.lower()
        if self.multi:
            selected, unknown = [], []
            for token in [t.strip() for t in norm.split(",") if t.strip()]:
                if token in self._index_map:                    # menu index
                    selected.append(self._index_map[token])
                elif token in self._value_map:                  # key / alias
                    selected.append(self._value_map[token])
                elif token in {"all", "none"}:               # shortcuts
                    selected = list(self._option_dict.values()) if token == "all" else []
                    break
                elif self.allow_custom:
                    selected.append(token)                     # custom
                else:
                    unknown.append(token)
            if unknown:
                plim.warn(f"⚠️ Invalid input: {', '.join(unknown)}")
                return _Retry
            return selected
        # single‑select
        if norm in self._index_map:
            return self._index_map[norm]
        if norm in self._value_map:
            return self._value_map[norm]
        if self.allow_custom:
            return raw
        plim.warn(f"⚠️ Invalid input. Expected one of: {', '.join(self._display_keys)}")
        return _Retry

    # map builders -----------------------------------------------------------
    def _build_maps(self):
        self._value_map = {}
        for k, v in self._option_dict.items():
            k_norm = k if self.case_sensitive else k.lower()
            v_norm = v if self.case_sensitive else str(v).lower()
            self._value_map[k_norm] = v
            if v_norm != k_norm:
                self._value_map[v_norm] = v  # alias via value
        self._index_map = {str(i + 1): self._option_dict[k] for i, k in enumerate(self._display_keys)}

    def _resolve_default_keys(self, default):
        def match(val):
            if isinstance(val, int) and 0 <= val < len(self._display_keys):
                return self._display_keys[val]
            if isinstance(val, str):
                cmp = val if self.case_sensitive else val.lower()
                for k, v in self._option_dict.items():
                    k_cmp = k if self.case_sensitive else k.lower()
                    v_cmp = v if self.case_sensitive else str(v).lower()
                    if cmp in {k_cmp, v_cmp}:
                        return k
            return None
        if isinstance(default, list):
            return [m for d in default if (m := match(d))]
        m = match(default)
        return [m] if m else []


# ──────────────────────────────────────────────────────────────────────────────
# Free‑form prompt (single or multi)
# ──────────────────────────────────────────────────────────────────────────────

@dataclass(kw_only=True)
class FreeformPrompt(PromptBase):
    """Collects arbitrary user text (once or repeatedly)."""

    multi: bool = False

    def _do_ask(self):
        if self.multi:
            values: List[str] = []
            while True:
                raw = plim.ask(f"{self.prompt} (or type 'done' to finish): ")
                if raw.lower() in {"done", ""}:
                    break
                values.append(raw)
                plim.plain("Current entries:")
                for i, val in enumerate(values, 1):
                    plim.plain(f" {i}. {val}")
                plim.plain()
            if not values:
                plim.plain("No entries provided.")
                return _Retry
            return values
        # single free‑form
        raw = plim.ask(f"{self.prompt}: ")
        return raw or _Retry


# ──────────────────────────────────────────────────────────────────────────────
# Convenience: Yes / No prompt
# ──────────────────────────────────────────────────────────────────────────────

class YesNoPrompt(OptionPrompt):
    """A Boolean prompt with "yes" / "no" shortcuts."""

    def __init__(self, prompt: str, *, default: str | None = None, **kwargs):
        super().__init__(
            prompt=prompt,
            options={"yes": True, "no": False},
            default=default,
            case_sensitive=False,
            multi=False,
            allow_custom=False,
            display="inline",
            **kwargs,
        )


# ──────────────────────────────────────────────────────────────────────────────
# Back‑compat façade
# ──────────────────────────────────────────────────────────────────────────────

def interactive_prompt(
    prompt: str,
    *,
    options: Union[Sequence[str], Dict[str, Any], None] = None,
    default: Union[str, int, List[Union[str, int]], None] = None,
    multi: bool = False,
    allow_custom: bool = False,
    freeform: str = "none",  # "none" | "single" | "multi"
    confirm: bool = False,
    retries: int = 3,
    case_sensitive: bool = False,
    display: str = "inline",  # "inline" | "menu"
):
    """Drop‑in replacement for the legacy `interactive_prompt` function.

    Routes the call to the appropriate class‑based prompt and returns its
    result (or ``None`` on failure/abort).
    """
    # --- free‑form modes ----------------------------------------------------
    if freeform in {"single", "multi"}:
        return FreeformPrompt(
            prompt=prompt,
            multi=(freeform == "multi"),
            retries=retries,
            confirm=confirm,
        ).ask()

    # If no options given, default to single free‑form input ------------------
    if options is None:
        return FreeformPrompt(
            prompt=prompt,
            multi=False,
            retries=retries,
            confirm=confirm,
        ).ask()

    # Option prompt ----------------------------------------------------------
    if isinstance(options, (list, dict)):
        return OptionPrompt(
            prompt=prompt,
            options=options,
            default=default,
            multi=multi,
            allow_custom=allow_custom,
            retries=retries,
            confirm=confirm,
            case_sensitive=case_sensitive,
            display=display,
        ).ask()

    # Defensive --------------------------------------------------------------
    raise TypeError("'options' must be list, dict, or None")
