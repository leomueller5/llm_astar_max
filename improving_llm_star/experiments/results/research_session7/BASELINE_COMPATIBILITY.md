# Session6 schema compatibility addendum

Observed during held-out response collection, before search-result inspection:
case`s7_15340003_0` produced a strictschema with1186enumvalues, exceeding the
provider's documented1000enumlimit. The API returnedHTTP400. Its fullworst-case
reservation remains held; no inferencecharge/refund is assumed.

PrimarySession7algorithm/prompt/sourcehashes are unchanged. Session6's literal
search/prompt/schema are also preserved. For unsupported schemas, literal
Session6 runs its already implemented provider-error geometric fallback. These
results are labelled`vm_strict2`, never silently replaced by a different method.

A separate stronger compatibility control`vm_hybrid2` keeps ALL candidate IDs
and map facts in the identical prompt, relaxes only the output enum to a string,
and validates returned IDs through the unchanged frozen decoder. This permits
real guidance on large maps instead of comparing only with a provider failure.
It is labelled as an adapter change, not a newly improved search algorithm.
Bothcontrols use identical model,temperature,seed,384outputcap and search code.
Supported-schema cases share one cached response between them. No candidate
truncation, solvedpath, or optimalreference information is introduced.

Source: [OpenAI Structured Outputs enum limits](https://developers.openai.com/api/docs/guides/structured-outputs).
The official limit check is deterministic and performed before further requests,
so repeated known-invalid schemas do not consume requests/reservations.
