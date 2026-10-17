# Style Contamination Guard

Use this reference whenever a task could inherit irrelevant details from a prior example, test prompt, named style, dialect request, nickname rule, catchphrase request, or BGM reference.

## Core Rule

The current user request controls the story's genre, character relationships, naming conventions, dialect, BGM, catchphrase density, image style, camera-movement style, and output depth. Examples calibrate format and specificity only; they do not become defaults.

## Do Not Inherit

Do not carry forward:

- old test prompts or sample plots
- single-character nicknames unless explicitly requested
- fixed family structures or character archetypes from examples
- dialect markers or regional slang unless explicitly requested
- catchphrase density unless explicitly requested
- named songs or BGM references unless explicitly requested
- black-comedy tone unless the current brief asks for it
- visual eras, film movements, filmmakers, named works, palettes, lighting motifs, atmospheres, lens habits, camera moves, or camera prohibitions from a style example

## Scope Reset

Before drafting, rebuild the current task profile from the current user request: mandatory premise, character objectives, decisive events, format, genre, relationships, naming, dialect, catchphrase density, music, reference works, image style, camera-movement style, and output depth. Mark every unspecified item as neutral rather than copying it from conversation history or examples. Treat replacement of the current premise with an unrelated premise as contamination even when the replacement is internally coherent.

Apply the detailed domain rules from their single owners:

- named-work abstraction and research: `open-source-research.md`
- short-form catchphrases and requested dialect application: `short-video-series.md`
- screenplay-derived image/camera grammar: `directing-and-shot-design.md`
- deleted canon facts, old event variants, and deprecated asset paths: `revision-canon-and-impact.md`
- names, relationships, genre, and all other creative facts: the current user brief

This file checks cross-task style/example leakage only. Do not place revision residue patterns or deleted-canon scan rules here.

## Final Check

Before final output, ask:

- Did the user request this dialect?
- Did the user request one-character names?
- Did the user request this family or role structure?
- Did the user request this catchphrase density?
- Did the user request this named song?
- Did the user request a series hook or recurring continuity device?
- Were the image and camera prompts derived from this screenplay rather than copied from a style example?

If not, remove it or make it generic.
