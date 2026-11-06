# The challenge and how it is scored

Source: docs/challenge-brief.txt, sections 1 to 3, 11 and "The point".

## What we are asked to build

An artificial system that shows a meaningful property of life. It does not have to be biological, an AI agent, or useful. The organisers want to see "computation starting to behave in ways that look increasingly like life": something that evolves, adapts, surprises its creators, and develops a world of its own.

The five properties they care about. These are areas of exploration, not checkboxes.

| Property | Their question |
|---|---|
| Autonomy | Does it act on its own, not just follow predefined instructions? |
| Persistence | Does it retain meaningful state, memory, identity or environment over time? |
| Adaptation | Does it change its behaviour from experience, feedback or changing conditions? |
| Interaction | Does it interact with other entities, its environment or other systems in interesting ways? |
| Emergence | Does complex or unexpected behaviour arise from simple mechanisms? |

**Hard rule: one property explored deeply beats five shallow ones.** Name the primary property in the README's "Why digital life?" and design the experiments around it.

## Scoring

| Weight | Criterion | How we earn it |
|---|---|---|
| 30% | Technical depth | Real mechanisms (selection, mutation, memory, learning, communication, environment modelling, quantitative analysis), well designed and correctly built. The interesting part is ours, not a library's or a prompt's. |
| 25% | Originality and creativity | An idea a judge has not seen ten times. Beyond conventional app development. |
| 20% | Behaviour and experimentation | The system demonstrably shows the property it claims. Measured across seeds, with controls, and with interesting observations, including surprises and failures. |
| 15% | Engineering and reproducibility | A judge can understand it from the docs and run a small version with one command. Pinned dependencies, seeds, configs, tests, expected outputs. |
| 10% | Effective, transparent tool use | Tools used well and AI use disclosed honestly. Jacob can explain the development process. |

What earns nothing: the largest model, the most tokens, the most agents, the most elaborate frontend. A polished UI cannot stand in for a technically interesting system.

What they explicitly don't want: "another wrapper around an API", "another dashboard", "another slightly different productivity tool". If an LLM is in the system, the life-like property has to come from the system around it, and the experiments have to rule out prompt effects.

What they value that most entries won't: "A negative result with good experimental methodology is more interesting than an unsupported claim of emergent intelligence."

## Decision test (apply before building any feature)

1. Which criterion does this raise, and by roughly how much of its weight?
2. Does it deepen the primary property, or spread us wider?
3. Can it be shown in the demo and measured in an experiment?
4. Can Jacob explain it in two sentences?

If it fails 2 or 4, don't build it. If it fails 3, it is polish: do it last or never.
