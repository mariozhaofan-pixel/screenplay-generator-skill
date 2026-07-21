# Style Contamination Guard

Use this reference whenever a task could inherit irrelevant details from a prior example, test prompt, named style, dialect request, nickname rule, catchphrase request, or BGM reference.

## Core Rule

The current user request controls the story's genre, character relationships, naming conventions, dialect, BGM, catchphrase density, and output depth. Examples calibrate format only; they do not become defaults.

## Do Not Inherit

Do not carry forward:

- old test prompts or sample plots
- single-character nicknames unless explicitly requested
- fixed family structures or character archetypes from examples
- dialect markers or regional slang unless explicitly requested
- catchphrase density unless explicitly requested
- named songs or BGM references unless explicitly requested
- black-comedy tone unless the current brief asks for it

## Scope Reset

Before drafting, rebuild the current task profile from the current user request: format, genre, relationships, naming, dialect, catchphrase density, music, reference works, and output depth. Mark every unspecified item as neutral rather than copying it from conversation history or examples.

Apply the detailed domain rules from their single owners:

- named-work abstraction and research: `open-source-research.md`
- short-form catchphrases and requested dialect application: `short-video-series.md`
- names, relationships, genre, and all other creative facts: the current user brief

## Final Check

Before final output, ask:

- Did the user request this dialect?
- Did the user request one-character names?
- Did the user request this family or role structure?
- Did the user request this catchphrase density?
- Did the user request this named song?
- Did the user request a series hook or recurring continuity device?

If not, remove it or make it generic.
