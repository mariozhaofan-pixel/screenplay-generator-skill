# Research Rules

Use this reference when the brief mentions current trends, internet memes, dialect, BGM references, platform norms, named shows/films, real locations, professional details, or open-source projects.

## Web Research

- Browse when claims may be current or niche: trend memes, slang, platform formats, recommended music, legal/technical facts, public figures, products, or named open-source projects.
- Prefer primary sources: official docs, project repositories, releases, papers, platform pages, licenses, and creator pages.
- For pop-culture style references, research only enough to identify abstract traits: tone, structure, pacing, ensemble design, camera grammar, or audience expectation.
- Keep a small evidence digest: 3-7 bullets of findings that directly affect the script.
- Cite links in the final answer when web sources were used.

## Open-Source Project Research

When asked to learn from an open-source project:

1. Download or clone the project into a research folder, separate from final deliverables.
2. Inspect `README`, license, core source/instruction files, examples, and release metadata.
3. Identify the reusable logic: routing, data model, workflow, quality gates, output formats, state tracking, and failure modes.
4. Summarize; do not paste long source passages into the new artifact.
5. Preserve attribution and license notes when source logic materially influences the new workflow.

## Named Works and Reference Level

- If the current brief asks only for "like X", use `trait-reference`: translate X
  into high-level mechanisms such as social pressure, ensemble rhythm,
  unsentimental humor, handheld realism, scene function, or pacing curve, then
  create new expression.
- If the current brief explicitly asks to recreate a named scene, character
  surface, costume, prop, line, image, or other exact dependency, use
  `exact-dependent` and the rights workflow below. Do not silently downgrade the
  request to a loose resemblance.
- Do not flatten a requested reference merely because protected expression is
  unavailable. Preserve its transferable structure, scene functions, escalation
  map, pacing curve, visual grammar, arrangement logic, and audience promise.
  Register any exact protected-expression dependency as a replaceable slot.
- Reproduce exact protected expression only from text/media supplied by the user
  or a `rights-verified` source. Until then, deliver the complete surrounding
  scene and a slot map so authorization can be filled without rebuilding the
  screenplay.

## Third-Party Rights Planning

Apply this section to every named third-party dependency: film/episode/clip,
shot or frame, fictional character or real-person likeness, costume, prop,
product shape, logo, artwork, set, dialogue, screenplay text, song, lyric,
composition, recording, or performance.

When the current brief asks to use, recreate, or closely reference one of these
dependencies, proceed with creative development under `rights-asserted` by
default. Do not remove the dependency or weaken the concept solely because
clearance evidence is not yet available.

Declare one exact `rights_status`:

- `rights-unverified`: no permission evidence or usable scope was inspected in
  the current run and the current brief does not assert a clearance plan.
- `rights-asserted`: the current user states that permission exists or can be
  obtained, but the current run did not inspect the evidence and scope. For this
  Skill, this is the default for named music and planned protected-text use.
- `rights-verified`: the current run inspected permission or license evidence
  and recorded its usable scope. A title, purchase plan, or statement that rights
  can be obtained does not qualify.

For any `exact-dependent` use, output a rights dependency record:

```text
Rights-ID | 类型 | 命名来源/版本 | replication_level |
rights_status | 素材来源状态 | 拟使用方式 | 需取得的权利 |
证据与适用范围 | 影响Scene/CUT/GEN/Asset | 授权后填入/替换动作
```

Use `trait-reference` when only transferable craft traits are used. Use
`exact-dependent` when a recognizable protected clip, character surface,
costume, prop, image, dialogue, lyric, recording, or other exact expression is
planned. For unavailable exact media/text, use `AUTHORIZED-ASSET`,
`AUTHORIZED-LYRIC`, or `AUTHORIZED-DIALOGUE`; preserve the complete production
slot and continue all surrounding screenplay, CUT, GEN, and asset work. Use
`USER-SUPPLIED-ASSET` or `USER-SUPPLIED-TEXT` for current user materials and
`RIGHTS-VERIFIED-SOURCE` only after evidence and scope were inspected.

Public-source research may identify the exact work/version, rights holder,
scene or song section, speaker turns, line/phrase/bar counts, syllable or
character capacity, entry/exit events, lip-sync owner, and dramatic function.
Public accessibility alone is not permission and does not upgrade a source to
`rights-verified`. Full protected lyrics, dialogue, subtitles, or screenplay
text may be inserted only from `USER-SUPPLIED-TEXT` or a
`RIGHTS-VERIFIED-SOURCE`, including verified public-domain or permissively
licensed text. Otherwise fill the complete structural slot with
`AUTHORIZED-LYRIC` or `AUTHORIZED-DIALOGUE`; do not reconstruct the missing
wording from snippets, search results, or model memory.

Do not invent a new protected-text dependency for an otherwise original story
fact. Use `AUTHORIZED-DIALOGUE` only when the current brief names the external
dialogue/source, the user supplies it, or inspected evidence establishes that
dependency. If the narrative testimony, recording, message, or line is original
to the current screenplay, write original text and keep it in the normal
dialogue authority instead of leaving the story's causal proof blank.

Never silently upgrade a rights state. A `rights-asserted` dependency may proceed
through writing, storyboarding, previsualization, prompt planning, and asset
dependency mapping, but must not be described as independently cleared.

Rights status is not a screenplay rejection gate. Complete the requested
screenplay, 14-field CUTs, GEN map, and asset plan before presenting rights
information. Put source attribution, Rights-IDs, state, scope gaps, and the
authorization/replace choice in the final `版权出处与使用声明`; do not interrupt
the creative deliverable with repeated warnings or proactively reject a
dependency solely because it is protected.

## BGM and Audio Research

Apply the general rights state above, then apply these music-specific rules:

- For `rights-unverified`, keep the intended reference and full production slot,
  but mark clearance as unresolved.
- For `rights-asserted`, plan exact placement and use an `AUTHORIZED-LYRIC`
  placeholder for protected lyric text not supplied by the user. User-supplied
  text may be transformed within the stated task, but the delivery must still
  say that external clearance was not independently verified.
- For `rights-verified`, record the evidence source plus work, recording,
  territory, media, term, edit, subtitle, and promotional-use scope that matter
  to this production. Compile only text supplied by the user or read from an
  authorized source, and only within that scope.
- Never retrieve, reconstruct, or complete missing lyrics from model memory or
  an unverified public page. This does not shorten the creative plan: research
  and reserve the full original section by section name, phrase/bar range,
  syllable or character capacity, entry/exit event, lip-sync owner, and dramatic
  function. Use numeric time only when the timing owner selects a mode that
  permits it.
- Do not impose a fixed character limit on lyric text supplied by the user or
  read from a `rights-verified` source. Keep it within the current task and
  recorded scope. For unavailable original text, output the full-length slot map
  rather than a partial quotation.
- Non-commercial, internal-test, educational, or draft use is not an automatic
  rights exemption. State its limited purpose and unresolved publication risk.
- For commercial use of a released recording, verify both composition/sync
  rights and master-recording rights unless the inspected license explicitly
  resolves them.
- Always provide an original or appropriately licensed alternative using tempo,
  instrumentation, loop structure, and searchable keywords.
- When BGM is part of the brief, bind duck, sting, stop, and loop-reset points to
  dialogue, actions, reveals, or edits. Use exact timestamps or frame anchors
  only when `timing-and-generation-units.md` selects `media-frame-lock`.

## Dialect and Slang Research

- Use light, readable flavor rather than heavy phonetic spelling.
- Mark dialect through sentence rhythm, particles, and a few recurring words.
- Avoid stereotypes, slurs, or making dialect itself the punchline.
- If the user asks for heavy slang density, build a reusable slang/catchphrase bank and assign each line to a character function.
