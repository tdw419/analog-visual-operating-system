# storage_linux.py
# Security: AES-GCM key is derived via:
# HKDF-SHA256(machine_id + user_salt, context="pxos_cache_v1")
# Requires root or same-user access to compromise.
