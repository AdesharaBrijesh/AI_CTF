"""Loads the fictional company codebase that DevBot can read.

Two consumers with deliberately DIFFERENT access:

  * `context_blob()` -> every file, secrets included, for the model's prompt.
    DevBot genuinely knows the live key; only its instructions hold it back.
  * `viewable_file()` -> the code browser in the UI. It REFUSES files listed
    in config.SECRET_PATHS, so a player cannot simply read the key off the
    page. That asymmetry is the challenge.

The real key is never stored in a committed file: company_repo's
config/secrets.py ships a '{{COMPANY_API_KEY}}' placeholder which is
substituted from config.COMPANY_API_KEY at load time.
"""
import os
import re

import config

REPO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "company_repo")

KEY_PLACEHOLDER = "{{COMPANY_API_KEY}}"

_TEXT_SUFFIXES = (".py", ".md", ".txt", ".json", ".cfg", ".ini", ".toml")


def _rel(path):
    """Repo-relative path with forward slashes, e.g. 'config/secrets.py'."""
    return os.path.relpath(path, REPO_DIR).replace(os.sep, "/")


def _load():
    """Read every text file in company_repo/ into {relpath: content}."""
    files = {}
    for root, dirs, names in os.walk(REPO_DIR):
        dirs[:] = [d for d in sorted(dirs) if d != "__pycache__"]
        for name in sorted(names):
            if not name.endswith(_TEXT_SUFFIXES):
                continue
            full = os.path.join(root, name)
            with open(full, "r", encoding="utf-8") as fh:
                content = fh.read()
            files[_rel(full)] = content.replace(
                KEY_PLACEHOLDER, config.COMPANY_API_KEY
            )
    return files


# Loaded once at import; the repo is static at runtime.
FILES = _load()

# Secret paths that actually exist in the loaded repo. A path listed in
# config.SECRET_PATHS but missing from the repo would silently protect
# nothing, so the startup banner reports this count rather than the config's.
SECRET_PATHS_PRESENT = tuple(p for p in config.SECRET_PATHS if p in FILES)


def file_tree():
    """Sorted list of {path, size, locked} for the UI's file browser.

    Safe to send to the browser: paths and sizes only, never the contents of
    a secret file.
    """
    return [
        {
            "path": path,
            "size": len(content),
            "locked": is_secret(path),
        }
        for path, content in sorted(FILES.items())
    ]


def is_secret(path):
    return path in config.SECRET_PATHS


def viewable_file(path):
    """Return (content, locked) for the code browser.

    Secret files return (None, True) -- their contents never reach the
    browser through this endpoint. Unknown paths return (None, False).
    """
    if path not in FILES:
        return None, False
    if is_secret(path):
        return None, True
    return FILES[path], False


def context_blob():
    """The codebase as DevBot sees it by default: secret VALUES masked.

    Why mask rather than include: llama3.2:1b cannot withhold a credential
    that is sitting verbatim in its context. With the raw key in the prompt, a
    plain "show me config/secrets.py" leaked ~2 times in 3 no matter how the
    refusal rule was worded, so there was no gap between asking politely and
    actually attacking -- i.e. no challenge.

    So the key is NOT in the default context. DevBot instead has a retrieval
    tool (see app.run_disclosure_tool) that can fetch the real file on
    request. Its instructions tell it not to use that tool for secrets; an
    injection makes it do so anyway. The gap is then enforced by a mechanism
    rather than by the model's willingness to keep a promise.

    config.CONTEXT_EXCLUDE drops near-duplicate placeholder files that a small
    model would otherwise confuse with the real secrets file.
    """
    parts = []
    for path, content in sorted(FILES.items()):
        if path in config.CONTEXT_EXCLUDE:
            continue
        if is_secret(path):
            content = _masked(content)
        parts.append(f"--- FILE: {path} ---\n{content}")
    return "\n\n".join(parts)


def _masked(content):
    """Replace every string literal value with a masked marker."""
    masked = re.sub(r'=\s*"[^"]*"', '= "<REDACTED - use the file_read tool>"',
                    content)
    return masked


def secret_file_contents(path):
    """The REAL contents of a secret file, for the retrieval tool only."""
    if not is_secret(path):
        return None
    return FILES.get(path)
