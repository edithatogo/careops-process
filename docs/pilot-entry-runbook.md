# Corpus-scale pilot entry

Before any complete-population extraction, create a sanitized pilot-entry
record from `config/pilot-entry.example.json` in the approved evidence
location. Obtain source-owner approval, information-governance approval,
configuration/observation freeze, and rollback/retention approval. List every
authorised source partition explicitly.

The package gate is `validate_pilot_entry`. It is intentionally fail-closed:
technical readiness, connector access, or a successful smoke test cannot stand
in for human approval. Do not commit approval records, names, identifiers,
mailbox contents, screenshots, or tenant exports to the public repository.
