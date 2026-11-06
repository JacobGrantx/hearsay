# Idea selection

Score each candidate 1 to 5 on the judging criteria before committing to one. The weights are the brief's. Pick the highest total that one property can carry deeply and that has a clear experiment with a control.

| Idea | Property it goes deep on | Technical depth (x0.30) | Originality (x0.25) | Behaviour and experiments (x0.20) | Engineering and reproducibility (x0.15) | Tool use (x0.10) | Weighted total | The control that would show the behaviour isn't hardcoded |
|---|---|---|---|---|---|---|---|---|
| TODO | | | | | | | | |

Filters before scoring:
- Can it show the property in a run of a few minutes on a laptop (for `make demo`)?
- Is there a mechanism to ablate and a baseline to beat?
- Can every team member explain the mechanism in two minutes?
- The brief says it does not want "another wrapper around an API". If an LLM is the core, the life-like property has to come from the system around it, and the experiments have to rule out prompt effects.
