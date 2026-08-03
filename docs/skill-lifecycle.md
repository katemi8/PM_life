# Skill Lifecycle

Этот документ описывает, как PM и агенты улучшают skills.

## Status

Active v0 process.

Current v0 should help identify repeated workflow problems, draft skill changes and route changes through PR, owner review and release checks after initial publication.

## When to Create or Improve a Skill

Create or improve a skill when:

- PMs repeat the same workflow several times;
- output quality depends on hidden prompt knowledge;
- the process touches Notion/KTalk/metrics and needs guardrails;
- review finds repeated agent mistakes;
- PMs need consistent output across products.

## Lifecycle

1. Ad-hoc workflow.
2. Repeated workflow.
3. Draft skill proposal.
4. Team agrees whether the skill change is needed.
5. Create branch and PR.
6. Owner reviews the change.
7. Run required checks.
8. Merge and release according to `docs/release-process.md`.
9. Monitor failures and improve.
10. Deprecate when replaced.

## Skill PR Must Include

- trigger phrases;
- scope;
- inputs;
- outputs;
- read sources;
- write targets;
- approval rules;
- failure policy;
- good/bad examples;
- smoke scenario.

## PM Contribution Flow

PM can ask the agent:

```text
Из этого повторяющегося процесса предложи изменение skill.
```

Agent should produce:

- current pain;
- proposed skill/change;
- expected inputs/outputs;
- guardrails;
- examples;
- suggested files to update.

The PM or agent then follows the repo process in `docs/release-process.md`.

## Skill Ownership

Initial skill owner is the person who created and first pushed the skill.

Owner responsibilities:

- review PRs that change the skill;
- keep the skill aligned with contracts and examples;
- decide whether behavior changes require version bump and release notes.

Agents must not change skill owner independently. If owner should change, the agent prepares the proposed change and asks PM/team to confirm.

## Deprecation

Do not delete a skill silently. Mark it deprecated and explain:

- replacement skill;
- migration path;
- removal date or condition.
