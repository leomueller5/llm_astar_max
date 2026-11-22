# Additional original-engine guidance ablation

Declared before final result inspection. Counts-only replay of original_goal_only
and robust_goal_only uses the same frozen original/corrected search engines,
geometry, start/goal and heuristic, replacing only the model reply by
Generated Path:[start,goal]. No API request and no heuristic inflation change.
Compare completed paired audit operations/costs with original and robust_original.
Five-second cap retained. This provides an operational query-level misleading-
guidance frequency, not an oracle label for each individual waypoint. No native
runtime claim is based on counts-only instrumented timings.
