# Meeting Review Packet Example

Status: current v0 example.

This is a read-only review packet. It helps a PM understand what was discussed in KTalk and what needs action. It does not write to Notion.

## Source Snapshot

- Meeting: `<KTalk title>`.
- Date/time: `<MSK date and time>`.
- Source window: `<timestamp range or transcript segment id>`.
- Related product area: `<feature/product area>`.
- Related Notion docs: `<links if found>`.

The packet should not include a full raw transcript. It should use short source anchors so the PM can verify the interpretation.

## Summary

Short product-level summary of what the meeting was about and why it matters.

Good summary:

```text
The discussion clarified the intended user behavior for the feature, but part of the business rule still needs PM confirmation before it can be safely reflected in official product docs.
```

Bad summary:

```text
The team talked about many implementation details.
```

## Agreement Candidates

| Item | Classification | Confidence | Source Anchor | Recommended Action |
| --- | --- | --- | --- | --- |
| `<atomic product rule>` | Final agreement | High | `<00:09:11-00:15:16>` | Can be used as draft input for a Notion doc after PM approval. |
| `<possible product rule>` | Directional agreement | Medium | `<timestamp>` | Ask PM to confirm before writing. |
| `<proposal>` | Proposal only | Low | `<timestamp>` | Do not write as agreed context. Keep as open question. |

Classification rules:

- `Final agreement`: participants clearly converged on one product rule.
- `Directional agreement`: the discussion points to a rule, but wording or scope is still incomplete.
- `Proposal only`: the team explored an option but did not agree to use it.

## Open Questions

Group unresolved questions by decision area, not by transcript order.

| Decision Area | Question | Why It Matters | Owner |
| --- | --- | --- | --- |
| Business rule | What exact condition triggers the behavior? | Implementation and analytics depend on the trigger. | PM |
| Data source | Which source should be treated as authoritative? | Prevents mismatches between product docs and backend behavior. | PM / Tech lead |
| Edge cases | Which rare cases should be supported now? | Separates release-blocking logic from later improvements. | PM |

## Conflicts And Gaps

| Type | Finding | Action |
| --- | --- | --- |
| Notion gap | The discussed rule is not reflected in the current Notion doc. | Prepare a proposed doc update, but do not write without approval. |
| Possible conflict | The meeting wording differs from the existing requirement. | Show both versions and ask PM which is correct. |
| Missing source | The transcript mentions a decision, but no owner/source doc is found. | Mark as needs confirmation. |

## Follow-Ups

- PM confirms which agreement candidates can become official product documentation.
- PM decides whether the existing Notion doc needs an update.
- Agent prepares a Notion diff if an existing document should be changed.
- Agent does not store raw transcript text in GitHub.

## Output Boundary

The packet can be used as input for:

- user story or requirements drafting;
- Notion doc update preview;
- analytics markup preparation.

The packet is not itself official product truth.
