# Director and Shot Design

Use this reference for the reasoning behind CUTs, camera decisions, actor blocking, focal lengths, visual continuity, director intent, and AI-video shot prompts. Do not redefine the output schema here; use `storyboard-output.md` for fields and order.

## Contents

- Story before coverage and the scene director map
- Global image-style and camera-movement prompts
- Primary shots, viewpoint, and reverse coverage
- Focal length, composition, depth, shot size, and camera height
- Spatial grammar, blocking, visual focus, and motion flow
- CUT/edit logic, viewpoint legality, responsibility shots, and transition phase
- Information control, AI-readable facts, and director checks

## Research Boundary

This workflow was refined through a local study, requested by the user, of three publicly shared craft videos by `老白的分镜`: the storyboard-practice primer and the upper/lower storyboard-course compilations. The source media, transcripts, keyframes, captions, and examples are not distributed with this skill. Only generalized directing and film-grammar rules are retained.

Focal-length conventions were cross-checked against official ARRI, Sony, and Canon lens documentation. Treat focal length, sensor size, camera distance, angle of view, perspective, aperture, and focus distance as related but distinct variables.

## Story Before Coverage

Do not begin with a standard wide/two-shot/reverse/insert recipe. For each scene, decide in this order:

1. `Scene task`: what meaningful story, relationship, information, or emotional change must land?
2. `What actually happens`: visible actions, prop changes, entrances/exits, pauses, looks, dialogue, and consequences.
3. `Key images`: the few images that make the scene's change understandable without explanation.
4. `Audience experience`: whose knowledge or feeling organizes the scene, what the viewer sees now, and what is delayed.
5. `Emphasis plan`: which information is essential, merely useful, or distracting.
6. `Camera plan`: framing, lens, position, movement, focus, and edit order that express the decisions above.
7. `Perception check`: whether a distracted first-time viewer will actually notice, understand, remember, and emotionally register the intended information.

A technically smooth sequence can still be weak if it only records events. Camera design earns its place by changing what the viewer notices, knows, anticipates, or feels.

## Global Image and Camera Style Prompts

Every delivered screenplay, including a screenplay without detailed CUTs, must be followed by this copy-ready block:

```text
【影像风格与运镜风格提示词】
**整体影像风格：** [one finalized prompt derived from this screenplay]
**统一运镜风格：** [one finalized prompt derived from this screenplay]
```

Build `整体影像风格` from the current script's era, region, genre, dramatic temperature, locations, weather, production design, characters, key images, and production limits. Resolve these into one coherent visual system: capture/rendering medium, texture, palette, contrast and exposure, highlight/shadow behavior, lighting motivation, atmosphere, material detail, skin/face treatment, and recurring character or location light locks when the story needs them.

Build `统一运镜风格` from the story's viewpoint, power relationships, action scale, performance needs, spatial design, and emotional progression. State the camera's default relationship to characters, preferred movement families, stillness/movement balance, composition, height/angle tendencies, lens tendencies, focus behavior, blocking coordination, visual-focus handoff, and story-specific practices to avoid. Use one coherent camera action per CUT; do not stack every available movement into each shot.

Rules:

- Derive both prompts only after screenplay facts are stable. They are a visual translation of the current story, not a reusable mood preset.
- Treat examples as specificity/format references only. Do not inherit their era, country, genre, directors, films, color palette, lighting, atmosphere, characters, props, or camera prohibitions.
- For `trait-reference`, convert named works or filmmakers into high-level visual
  mechanisms and combine them with current story facts. For an explicitly
  requested `exact-dependent` scene, character surface, costume, prop, or frame,
  keep the requested production dependency and route its Rights-ID/source state
  through `open-source-research.md`.
- Do not force constant motion, handheld shake, Dutch angles, backlight, fog, grain, shallow focus, or any other technique unless the current screenplay benefits from it. Static or eye-level framing can be the correct style choice.
- Keep the two prompts physically and aesthetically compatible. Avoid mutually exclusive capture media, contradictory light directions, impossible camera paths, and adjective piles with no visible consequence.
- Let the global prompts define the shared grammar. Per-CUT photography must instantiate that grammar and state only scene-specific execution or a motivated deviation; never paste the full global block into every CUT.
- Include character- or location-specific visual locks only when they follow from the current screenplay and need continuity across scenes.
- Do not include runtime, scene/CUT durations, timecodes, or timing budgets.
- Output one resolved version of each prompt, not alternatives or a menu.

## Scene Director Map

Before writing CUTs, define one compact map per scene:

```text
Scene/beat IDs:
Event ID and event identity:
Scene task and meaningful change:
Audience alignment/knowledge:
Viewpoint mode, owner, presence, and legal entry/exit triggers:
Key images/drama points:
Important vs. merely useful information:
SCN-ID, location map, and fixed landmarks:
Character/prop starting positions:
Action axis, eyelines, and screen directions:
Entrances, exits, and offscreen space:
Base lens / emphasis lens / insert lens palette (35mm equivalent):
Lighting, time, weather, color, wardrobe, and prop continuity:
Emotional curve:
Sound anchors:
Responsibility image, if the scene contains a consequential choice:
Transition mechanism and phase handoff:
```

Use the map as a continuity lock, not as an excuse to omit per-CUT facts.

## Key Images and Information Hierarchy

- Build the scene around key images that carry the dramatic change.
- Introduce important props before their payoff, then preserve location and state.
- Give important actions more visual weight through sustained attention, closer framing, reaction, contrast, repetition with changed meaning, or a deliberate framing jump.
- Let merely useful movement pass smoothly and quickly. Do not make every entrance, line, or gesture equally prominent.
- Use reaction shots when the reaction changes audience interpretation, not as automatic dialogue coverage.
- Delay a reveal when suspense or emotional alignment benefits from it. Offscreen sound, eyeline, and reaction can hold information before the confirming image.
- Start on the most useful image. An establishing wide shot is optional; reveal geography later when that better serves the story.

## Primary Shots and Coverage

- Use `primary shot / 主镜` here for an indispensable target image inferred from the screenplay, surrounding story, and scene purpose. A scene may have several primary shots and one primary image among them.
- Do not confuse this with a conventional wide safety master. A continuous master may carry geography, performance, or spatial tension, but it is only one possible tool.
- Place the certain primary shots first. Derive subject groupings and action axes from those target images, then use reverse coverage or connective images only where the scene still has an information, emphasis, viewpoint, continuity, or rhythm gap.
- Return to a wider relationship view when the viewer needs to re-read geography or a changed relationship. Do not return by habit.
- Derive inserts and reactions from the scene's dramatic points, not from a checklist.

## Viewpoint and Reverse Coverage

- Distinguish objective observation, character-aligned observation, literal POV, and temporarily omniscient information. State which mode controls each CUT, who owns it, whether that person is present, what the audience currently knows, and what visibly triggers entry or exit.
- Literal POV is legal only when its owner is physically present or is demonstrably watching/remembering the represented media. A scene the character never witnessed cannot be presented as that character's literal first-person view.
- Enter a subjective view only after a visible attention, action, eyeline, sound, or media trigger. If the audience must first understand geography, responsibility, or an objective fact, establish that fact in an objective image before aligning subjectively.
- Do not let viewpoint manufacture knowledge. A character-aligned CUT may restrict or color what the audience perceives, but it cannot reveal information unavailable to that character without declaring a temporary omniscient mode.
- After a protagonist says something harmful or makes a consequential choice, use an objective `responsibility shot` when omitting the recipient's visible result would hide causation, blur accountability, or let subjective immersion excuse the actor.
- Reverse coverage does not need to be mechanically symmetrical. Vary clean singles, over-the-shoulders, profile relationships, obstruction, camera distance, and lens when power, intimacy, concealment, or isolation changes.
- Preserve eyelines and screen side across reverse angles unless a visible reset or deliberate rupture motivates the change.
- When dialogue continues over another image, state whether the speaker is on-screen, off-screen, or voice-over and whether lip sync is required.

## Composition and Depth

- Begin with the location, performers, and props the story actually provides. Arrange existing elements by camera position and blocking before forcing an abstract composition template onto the scene.
- Organize foreground, midground, background, overlap, relative scale, perspective lines, visible surfaces, light/color separation, focus, and parallax so a flat frame communicates three-dimensional space.
- Reveal more than one surface of an important object or location when depth and orientation matter; a straight-on view may intentionally flatten the image when distance, rigidity, or graphic clarity is the goal.
- Use density/sparsity, grouping, bands, leading lines, symmetry, or imbalance only when they support visual clarity and story meaning.
- Do not add unrelated set dressing merely to manufacture depth. Every foreground or background element should support geography, mood, action, information, or continuity.

## Focal Length and Camera Position

Use `35mm-equivalent focal length` unless the camera format is known. If the format is known, state both the actual lens and its 35mm-equivalent angle of view.

Never specify focal length alone. Pair it with:

- shot size
- camera-to-subject distance
- camera height and vertical angle
- horizontal angle and relation to the action axis
- composition and background content
- focus target, depth plan, and any rack focus
- reason this combination serves the story

Working palette, as flexible heuristics:

| 35mm equivalent | Typical visual use | Risks/checks |
|---|---|---|
| 18-24mm | strong depth, immersive proximity, cramped interiors, energetic movement | edge distortion, excess background, exaggerated distance |
| 28-35mm | contextual character coverage, close spatial relationships, mobile staging | foreground dominance and busy edges |
| 40-55mm | balanced relationship view, restrained observation, neutral-feeling coverage | can become visually generic without composition or blocking intent |
| 65-100mm | isolation, compressed relationships, reaction detail, controlled background | reduced spatial context, harder focus, distant camera position |
| 100mm+ / macro | remote observation or decisive object/detail inserts | over-isolation, unstable continuity, impractical working distance |

Framing is produced by lens plus camera position. For the same sensor and subject size, a wider lens requires a closer camera and shows more background with stronger apparent depth; a longer lens requires a farther camera and shows less background with greater compression. Sensor size changes angle of view. Do not write `wide shot = wide lens` or `close-up = telephoto` as fixed rules.

Perspective is governed by camera position. Lens choice changes angle of view and often causes the camera to be repositioned for the desired framing; do not claim that changing focal length alone changes perspective when camera position stays fixed. In a final CUT, choose one focal length rather than an unresolved range.

Keep a restrained lens grammar inside a scene. Change the palette when the story changes subjectivity, distance, pressure, or information priority, and state that intent.

## Spatial Grammar

- Establish the action axis, character eyelines, and screen direction before coverage.
- With three or more characters, state the active pair or group for each beat. A new interaction can create a new axis; bridge to it with a frame containing the old and new subjects, a neutral relationship view, or visible character/camera movement.
- Treat grouping as meaning: placing two characters together against a third can imply alliance or pressure. Do not create that relation accidentally through coverage.
- Keep left/right movement and looks consistent unless a motivated reorientation is shown.
- For dialogue, choose reverse angles from relationship and viewpoint, not mechanical symmetry.
- Make foreground, midground, background, doorways, obstacles, and offscreen space explicit.
- Match action across cuts when continuity should feel seamless.
- A neutral angle, visible camera move, character movement, or clear spatial reset can support an axis crossing.
- Cross or break the axis only when disorientation, reversal, separation, or a new spatial fact is intended and the audience can recover the scene.
- Derive camera position from the target image and spatial relationship. Do not place a camera arbitrarily and accept whatever frame results.
- Use an insert for a local object, body detail, or reaction only when it establishes, emphasizes, pays off, redirects focus, or bridges continuity.

## Composition, Height, and Visual Focus

- State camera height from the subject's supporting floor/ground plane and state tilt separately. Use height and vertical angle to control background exposure, hierarchy, vulnerability, surveillance, viewpoint, or neutrality. Do not label high/low angle without explaining the relationship it creates.
- Track horizon/eye-height logic, vanishing direction, foreground/background scale, and repeated character height across connected images. Deliberate changes need a viewpoint or emotional reason; accidental changes make the space feel unstable.
- Establish one primary visual focus per CUT. Direct attention with placement, scale, contrast, focus, motion, eyelines, foreground obstruction, or sound.
- Preserve or deliberately redirect the viewer's visual focus across the edit. Match gaze, motion, or compositional position for flow; break it only for a motivated surprise, collision, or power shift.
- Change shot size enough to be legible. Avoid accidental near-duplicate framings; use an intentional jump only when the emphasis or disruption is the point.
- For moving shots, keep the composition valid at the start, during the move, and at the end. State the movement trigger and stopping condition.

Visual focus can be driven by motion, faces/eyes, salient objects, contrast, focus, leading lines, eyelines, occlusion, or sound. Track its approximate screen position at the start and end of every CUT. Keep the intended information visually available until it is legible, then leave on a motivated story, action, perception, or sound change; describe that logic without duration values.

Fast movement creates visual inertia. If the viewer's gaze exits toward one edge, place or introduce the next focal subject where that gaze is likely to arrive. A deliberate focus jump can mark a new section, shock, collision, confusion, or climax, but state that purpose.

## Shot Size and Rhythm

- Choose the primary shot size from the content: facial or hand detail usually needs tighter framing; full-body movement, staging, and geography usually need more space.
- Avoid accidental same-size, same-position cuts between different subjects that make one body appear to transform into another. Change angle, background, scale, focal position, or add a motivated bridge.
- Gradual tightening can increase pressure and gradual loosening can release or close a beat. Reserve the tightest and loosest images for the primary story moments; add connective coverage only for an unresolved information, viewpoint, geography, continuity, or rhythm gap.
- Do not treat alternating loose/tight framing as automatically wrong. Character-aligned viewpoint, inserts, reactions, paragraph breaks, and deliberate emphasis can justify it.
- Shot size is one rhythm variable alongside movement, angle, sound, performance, and edit order; do not optimize it in isolation.

## Motion Flow

- Reduce complex movement to a dominant screen-space vector for the subject, camera, or important prop: left/right, up/down, toward/away, still, or a clear turn between vectors.
- Matching dominant vectors across CUTs creates flow even when the subject changes. Reversing or colliding vectors creates friction and a rhythm change; use it deliberately.
- For complex action, design the broad motion blocks and their handoffs before adding detailed poses, gestures, impacts, or effects.
- Distinguish subject movement from camera movement. State which one carries the visual focus and how the frame settles.

## Actor Blocking and Performance

For each CUT, write:

- start position: screen-left/center/right plus foreground/midground/background
- facing direction and eyeline target
- trigger for movement
- route, speed, and interaction with people or props
- end position and body orientation
- hand/action continuity when a hand, prop, contact, or unfinished action crosses the CUT boundary
- visible performance change

Use `dialogue-performance-and-sync.md` for the authoritative performance chain and dialogue doctor. This file only translates the approved performance into camera-readable blocking. Do not invent a second emotion vocabulary or independently rewrite dialogue here.

Do not overload a CUT with several independent actions. If a video model would have to invent which action matters, split the CUT.

## CUT and Edit Logic

One `CUT` is one uninterrupted camera segment between edits. A continuous pan, dolly, or focus pull remains one CUT if time and space remain continuous. Start a new CUT when any of these changes materially:

- camera setup or viewpoint
- time or location
- dominant subject/action
- information task
- independent insert or reaction

Every cut needs a reason. Common motivations include action match, eyeline answer, reaction, reveal, concealment, rhythm change, dialogue power shift, sound cue, graphic match, or deliberate contrast.

Cut on story and perception changes rather than punctuation. Expand a key beat into multiple CUTs only when added detail, viewpoint, action, or reaction increases meaning. Merge or delete coverage that merely repeats known information.

A separate model prompt does not create a CUT. Use `timing-and-generation-units.md` to package one or more editorial CUTs into a `GEN` production unit. CUT boundaries express edits; GEN boundaries express model cold starts, production limits, asset/state compatibility, and review handoffs.

## Transition Phase

Design transitions only after event, performance, viewpoint, and continuity facts are stable. Use one primary mechanism per transition; one supporting sound bridge is acceptable.

Record:

`story function -> source image/action phase -> cut point -> destination image/action phase -> continuity variable`

- Both sides of an action match must have independently valid start and end states.
- The cut point must occur after every action and audible word assigned to the
  current CUT. If sound intentionally crosses the edit, label the split or
  overlap and map the remaining audio to the destination CUT. A transition
  field may not cut before the CUT's final listed line or action and then leave
  that content unmapped.
- Do not suspend an incomplete action across a long story gap merely to create a graphic match.
- Do not invent a prop, passerby, foreground wipe, or camera flourish solely to hide the edit.
- A cross-time or cross-space transition must clarify the new state on arrival. Use a separate transition GEN only when the transition itself is the production unit's main task.
- Memory, recognition, and association need a mechanism that matches the character's awareness; a random foreground wipe is not a substitute for causality.

## Information Control

- Decide what is visible now, what remains offscreen or occluded, what is inferred through sound/eyeline/reaction, and when confirmation arrives.
- Delayed information must create a fair question, suspense, alignment, or emphasis. It cannot hide facts the chosen viewpoint plainly should reveal without a motivated obstruction.
- A reveal gains weight when the viewer has invested attention in resolving it. Pay it off with a clear confirming image or sound and update the scene's information ledger.

## AI-Readable Visual Facts

For each CUT, include a compact visual-facts paragraph that can seed an image/video prompt:

- use character names, not ambiguous pronouns
- state exact spatial relationships and screen direction
- state the dominant action in chronological order
- identify the important prop and its state
- state lens/framing/camera movement and focus target
- state visual-focus start/end positions and dominant motion vector
- state lighting/time/weather and continuity anchors
- describe the visible emotional performance
- state the start image/state, chronological action, and end image/state when motion is important

For dialogue, use the exact derived fragment format in `dialogue-performance-and-sync.md`. Include only words audible during the CUT and never rewrite a locked line from the storyboard surface.

Do not mix alternative options in a final CUT. Do not write `同上`, `按剧情`, `自由发挥`, or hidden psychology. Resolve the decision.

## Director Intent

Director intent must explain the viewer effect, not repeat the action. A useful sentence answers:

- What must the viewer notice?
- What does the viewer learn or temporarily not learn?
- Whose experience organizes the frame?
- Why this lens, position, movement, or cut now?
- What story or emotional change does the CUT hand to the next CUT?

After assembling the sequence, test three separate layers:

1. `Actual event`: all required actions, lines, reactions, props, and outcomes exist.
2. `Selected experience`: the edit shows or withholds the intended subset in the intended order and viewpoint.
3. `Perceived result`: visual focus, contrast, reaction, repetition, sound, edit order, and context make a first-time viewer actually register the priority rather than merely allowing it to appear somewhere in frame.

Weak: `展示她签字。`

Strong: `先让观众停在她迟迟不落笔的手上，再切对方回避的视线，把“关系已结束但双方都未准备好”变成可见事实。`

## Final Director Check

- Can the scene task be named in one sentence?
- Are the key images more prominent than routine information?
- Does every CUT change story, emotion, knowledge, rhythm, or continuity state?
- Is every literal POV legal, visibly triggered, and free of unavailable knowledge?
- Does any consequential harmful choice receive an objective result image when accountability would otherwise be obscured?
- Does every transition state one mechanism and a valid source/cut/destination phase handoff?
- Are lens, position, framing, and focus physically coherent?
- Can actors execute the blocking without guessing?
- Can an AI video model identify one dominant action and stable subject per CUT?
- Are axis, eyeline, screen direction, props, wardrobe, lighting, and geography continuous?
- Does the final image complete the scene's meaningful change or launch the next one?
