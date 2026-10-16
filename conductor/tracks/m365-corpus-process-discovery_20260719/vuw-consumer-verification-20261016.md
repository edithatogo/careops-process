# Bounded VUW consumer verification — 16 October 2026

Actual private test artifacts were read in memory; no private facts, identifiers,
keys or additional retained evidence files were created. The current repository
CollectorMailFact, CanonicalMailFact and FolderPage strict models accepted both
source acquisitions, destination facts and both page records.

Verified: 30 unique messages in each acquisition and destination; exact canonical
source/destination/replay equality; one exhausted page per acquisition; page
membership and candidate/acquired counts of 30; page folder matches the bounded
scope descriptor; all fact timestamps lie inside the frozen observation window;
retention/configuration flags true; configuration and approval canonical hashes
match the manifest. Initial-source canonical JSON digest matches the recorded
initial replay-comparison hash. Schema/value checks ran in a separate Python
process from acquisition and passed.

The inventory is an Inbox-only scope descriptor, not the full FolderEntry
contract: it lacks parent/disposition/reason/children enumeration and source
population denominator fields. An attempted strict FolderEntry validation
correctly rejected it. No fields were invented to make it pass. Source counts
are source-reported observations, not independent population ground truth.
No Dataverse reconciliation, full-mailbox coverage or pilot completion is
claimed. Evidence remains smoke_test with a local destination. The full closed
report pipeline was not invoked against incompatible inventory evidence.

Completion: 2026-10-16T03:02:12.371001Z. Approved disposal due:
2026-10-23T03:02:12.371001Z (23 October 2026, 1:02 pm Brisbane).
The coordinator owns scheduling the original 14-file/key allowlist; this
verification did not extend it. Queensland Health pilot gates remain open.
