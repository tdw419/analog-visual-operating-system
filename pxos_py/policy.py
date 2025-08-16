# policy.py
# edid_sha256_allow uses fnmatch:
#  - 'ab12*'  => prefix match
#  - '*ab12'  => suffix match
#  - 'ab12'   => exact match only
def _edid_allowed(hash_hex: str, patterns: list[str]) -> bool:
    from fnmatch import fnmatch
    return any(fnmatch(hash_hex, pat) for pat in patterns)
