# Screenplay Generator Skill

Codex skill for turning rough story ideas, genre briefs, short-video prompts, episodic concepts, or storyboard requests into executable screenplay and shot-list drafts.

Display name: 剧本生成器  
Skill folder: `screenplay-generator`

## What It Does

- Expands loose story ideas into shootable screenplay/storyboard drafts.
- Produces beat sheets, shot tables, dialogue scripts, BGM/sound plans, and continuity notes.
- Supports short videos, episodic unit drama, web-series bibles, and production-ready分镜剧本.
- Uses web and open-source research when current facts, trend references, dialect, BGM, named works, or project logic matter.
- Guards against style contamination: examples and test prompts do not become defaults.

## Installation

Copy the `screenplay-generator` folder into your Codex skills directory:

```powershell
Copy-Item -Recurse .\screenplay-generator $env:USERPROFILE\.codex\skills\
```

Then start a new Codex session and ask to use `$screenplay-generator`.

## Usage Example

```text
Use $screenplay-generator to turn this premise into a 90-second vertical short-video storyboard:
A night-shift convenience-store clerk discovers every customer is buying the same item for different secret reasons.
```

## Source and Attribution

This skill was built from original workflow design plus research into the open-source MIT-licensed project:

- `Shanyin-ai/shanyin-screenwriting-master`

The source project contributed high-level screenwriting workflow ideas such as format routing, visual writing discipline, self-checks, pacing, and continuity management. This repository does not copy the source project's long-form prompt text.

## License

MIT License. See `LICENSE`.
