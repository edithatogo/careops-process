# Source-linked credentialing pathway references

`credentialing_pathways.py` compares one explicitly authorised case against a
supplied versioned reference. The reference names its source, pathway,
authority mapping, ordered required stages, permitted activities and terminal
activities. It does not supply clinical policy or grant approval.

The interface admits routine renewal, changed scope, mutual recognition,
temporary approval, conditions/supervision, review/appeal and register
reconciliation. Each uses its own supplied stage list. Synthetic examples show
that the comparator does not silently substitute the renewal model; they do not
establish the actual requirements of any organisation or pathway.

Only observed case-linked events count. Missing/repeated/out-of-order stages,
wrong pathway or authority, unexpected activities, tied event timestamps,
missing terminal events and work after a terminal event require review. A
case with no observed evidence remains insufficient. Inferred events never
establish execution. References and projections are revalidated before use.

The caller must supply a trusted case-analyst role and an explicit case grant
set. The function does not authenticate those inputs. The assessment is
restricted case evidence, not an aggregate report, professional-competence
judgment or compliance certificate. A `matches_reference` result describes the
observed event sequence against that supplied reference only.

The strict wire shape is in
[the reference schema](../contracts/credentialing-pathway-reference.json).
Registered activities and bounded reference codes replace free text. Actual
Queensland Health/CHHHS source mappings, authority versions, retention, case
access and pathway acceptance remain required external evidence.

## Recovery and verification

After the implementation chat stopped with a rate-limit error, its uncommitted
source and tests were found to contain null-byte regions and unrelated content.
The coordinator preserved damaged copies privately and reconstructed the
recorded file-writing and patch operations from tool history. Committed source,
tests and scripts were separately compared with Git object hashes: all 120
tracked files matched after accounting for checkout line endings.

The reconstructed suite exposed the author's unfinished post-terminal regression
(35 tests passed, one assertion failed). The comparator was changed to report
`activity_after_terminal`; all 36 pathway tests then passed. Scoped lint,
formatting, strict typing and Bandit passed. One full integration run passed
799 tests, using its own coverage dataset and no pytest cache provider.

These receipts establish local behavior at this checkpoint. They do not prove
host/storage repair or fulfil live policy, silent-mode, pilot or manual gates.
