# Minibus (Danfo) project: handover context

This file is for a new Claude session picking up this work. It summarises the
earlier session: what the user asked for, what was built, how the tools work,
the rules the user cares about, and what is still open. Read all of it before
touching anything.

- **Repo:** `BelovedTemitope/blenderproject_GetItThere`
- **Working branch:** `claude/minibus-v03`. Nothing has been merged and no PR
  was requested. Don't open one unless asked.
- **User:** Beloved Temitope (3D artist on the GAMR team, building Roblox
  vehicles). Commit as `-c user.name=BelovedTemitope -c user.email=belovedtemitope@yahoo.com`.

---

## 1. The original goal

> Finish modeling the bus in `GIT_Veh_Minibus_Blockout_v02.blend` using the tires in
> `ILikeTheTires.blend`. Pay attention to detail, be accurate and logical.
> `Minibus_vehicle_showcase_render_2K_20261017000657.jpg` is the **ultimate reference**,
> followed by `Using_this_EXACT_vehicle_as_2K_20261017174511.jpg` for **part reference**.

Other references in the repo root:
- `M3_Exo_Runner_Ortho_3rdAngle_Projected_Colour.png`
- `M3_Exo_Runner_Ortho_3rdAngle_Projected_Pencil.png`

These are ortho sheets used for proportions and front-view shape.

The vehicle is a Lagos "danfo" minibus (VW T3 style). It has:
- an exoskeleton roll cage, a roof rack with luggage, a light bar and a roof wing
- a bull bar, tow shackles and a skid plate
- a rear ladder, a spare tyre carrier and an exhaust stack
- an interior with front seats, two benches, a dashboard and a steering wheel
- livery decals: dark-navy swoosh bands and an "01" roundel on an orange/ochre body

## 2. The user's standing rules (important)

1. **Topology:**
   - Clean, mostly quads, avoid n-gons.
   - Tris are allowed only where the user explicitly allowed them (the `_tris` / v06 variants).
   - The user later asked for "predominantly quads, tris permitted when necessary" when optimizing.
2. **Fit and flow:** parts must fit and flow into each other. No ugly intersections or overshoots.
3. **Real-world function:**
   - Seats are real seats: a cushion and backrest meeting at a hinge, a pedestal, and a headrest on posts.
   - Never "floating subdivided cubes". A previous chat applied one subdivision to cubes and the user hated it.
   - Every part should look functional: hinges, mounts, brackets and so on.
4. **Iterate against the references:**
   - Render every side and compare.
   - The user wants to see renders, as contact sheets.
5. **Versioning (very important):**
   - Every change is a **new .blend file**. Never modify an earlier version unless the user explicitly asks.
   - The only time they did ask was the wheel rim fix in v05 and v05_tris.
   - All blend files go into git. Renders go under `renders/<version>/`.
6. **Don't break what works:**
   - When adding a feature, only modify the parts involved.
   - Optimizations must not visibly change the model.
7. The user often interrupts and redirects. When they say "scratch that", follow the new instruction.

## 3. Files in the repo

| File | What it is |
|---|---|
| `GIT_Veh_Minibus_Blockout_v02.blend` | User's original blockout (input, saved in Blender 5.2). Never edit. |
| `ILikeTheTires.blend` | Tyre meshes (WheelFL/FR/RL/RR, SpareTyre) the user likes. Input. |
| `..._v03.blend` | First full model. |
| `..._v03withRidges.blend` | v03 + raised T3 swage lines (ridges). |
| `..._v03shape_and_mirror_adjusted.blend` | + front-view tumblehome taper (matches the front-view ref) + real-size mirrors. |
| `..._v04.blend` | Ridges made **negative** (grooves into the body), shape, mirrors, and the cage rebuilt "straight and clean" (the user said the cage was messy at the front). |
| `..._v04_SlidingDoors.blend` | v04 + separate, closed, flush sliding doors on both sides (`Door_Sliding_L/_R`, pivot at door centre). |
| `..._v05.blend` | **Current preferred version.** Optimized v04_SlidingDoors: hidden faces and caps removed, flat-face loops dropped, lighter decals, all quads (20k quads, ~41.9k tris evaluated). |
| `..._v05_tris.blend` | v05 + planar dissolve and triangulation (tris allowed), ~37.8k tris. |
| `..._v05_StudioScenes.blend` | v05 + two extra Scenes `Studio_Light` and `Studio_Dark` (cyclorama, area-light rig, camera, AgX). **This is the file sent to the team.** It still has the rim-material bug (see §7). |
| `..._v06.blend` | Game LOD experiment at **6,993 tris** (collapse-decimated to per-part budgets; left door removed to show an open doorway). The user found it **unsatisfactory: too much form lost**. Not rejected, but not the direction to take. |
| `renders/<version>/` | Contact sheets and renders per version. `renders/studio/` holds the light and dark presentation renders. |
| `tools/minibus/*.py` | The procedural build pipeline (see §4). Every .blend from v03 on is generated from v02 by these scripts. |
| `tools/minibus/dev/*.py` | Review helpers (preview renders, contact sheets, image diff, tri counts). |

## 4. Environment and tooling

### Headless Blender

The scripts use the **pip `bpy` module**: Blender 5.2.2 LTS on Python 3.13. It was
installed into a uv venv at `/opt/bpyenv`, with numpy and Pillow alongside. That
venv won't exist in a fresh container. To recreate it:

```bash
uv venv /opt/bpyenv --python 3.13      # or: python3.13 -m venv /opt/bpyenv
/opt/bpyenv/bin/python -m pip install bpy==5.2.2 pillow   # (uv pip install --python /opt/bpyenv/bin/python bpy==5.2.2 pillow)
```

Run scripts as `/opt/bpyenv/bin/python script.py -- args`.

Gotchas:
- `import bpy` **before** `bmesh`.
- Never name a script after a stdlib module. A file called `inspect.py` crashed bpy.
- `pkill -f` / `pgrep -f` match the shell's own command line and kill it. Use `ps -eo pid,args | grep "[m]b_studio.py"` instead.

### Build

From the repo root:

```bash
/opt/bpyenv/bin/python tools/minibus/mb_build.py -- . <out.blend> <variant>
```

Variants:

| Variant | Produces |
|---|---|
| `v03` | v03 |
| `ridges` | v03withRidges |
| `shape` | v03shape_and_mirror_adjusted |
| `v04` | v04 |
| `v04doors` | v04_SlidingDoors |
| `v05` | v05 |
| `v05tris` | v05_tris |
| `v06` | v06 |
| `v06quad` | **stub**: LOD geometry, no decimation, no triangulation. Never finished (see §8). |

`mb_build.py` opens v02, configures `mb_body` flags, sets `mb_lib.OPTIMIZE` / `mb_lib.LOD`,
runs every module's `build(ctx)`, then optionally runs `mb_optimize.cull_hidden()`,
`planar_tris()` and `lod_budget(LOD_BUDGET)`. A build takes about 5 s.

Build into a scratch path first. Copy the result into the repo under a **new**
name only when it's good.

### Review helpers (`tools/minibus/dev/`)

- **`preview.py -- file.blend outprefix view...`** renders review images (Cycles CPU, 48 samples, 1376×768, sun plus a grey world, flat colours by object name).
  - Views: `fl fr rl rr side side_r front rear top fl_close cage_fl cage_top cage_fr cage_front door_close door_close_r cargo seats cab band under rear_close rr_close cut_int cut_chassis cut_under`.
  - **Render `cut_*` views in a separate call.** They hide the body for every view in the same call.
  - About 30 s per view on 4 cores.
- **`sheet.py out.png cols img...`** builds a contact sheet.
- **`diff.py`** diffs images.
- **`count.py -- file.blend`** prints evaluated tris per object and per collection.
- **`parts.py -- file.blend`** gives tri totals for the ClickUp parts (livery, rack, luggage, doors).
- **`wtopo.py -- file.blend`** prints wheel topology and material indices.
- **Validation and overlap checks** live in `tools/minibus/`, not `dev/`:
  - `mb_validate.py -- file.blend` counts quads, tris, n-gons, non-manifold edges and doubles.
  - `mb_overlaps.py` lists BVH overlap pairs between parts.

### Presentation renders

- `tools/minibus/mb_studio.py -- file.blend out_dir light|dark [shots] [--preview]`
  - Shots: `hero_fl hero_rl side high_fr detail`.
  - Final quality is 96 samples at 1920×1080 with AgX Medium High Contrast.
  - The user only wanted two images (light and dark `hero_fl`), in `renders/studio/`.
- `tools/minibus/mb_scenes.py -- in.blend out.blend` adds the Studio_Light and Studio_Dark scenes.
  - The vehicle collection is linked, not copied, into both scenes.
  - Lamp glow is set per scene through an Attribute node reading the scene property `mb_glow`.

## 5. Model conventions

- 1 Blender unit = 1 Roblox stud.
- Axes: front is **−Y**, +X is the vehicle's **left** (LHD driver side; the left side
  is the kerb side with the sliding door), Z is up.
- Wheels:
  - centres at x ±3.95, y −5.28 (front) / 4.31 (rear), z 1.83
  - tyres scaled by 1.83/1.95
  - spare at (−1.55, 8.17, 5.72)
- Overall bbox: 18.91 L × 9.60 W × 12.14 H, including cage, rack and cargo.
- Collections:
  - Everything sits under `GIT_Veh_Minibus`.
  - Sub-collections: `Minibus_Body`, `Minibus_Chassis`, `Minibus_Front`,
    `Minibus_Rear`, `Minibus_Cage_Rack`, `Minibus_Interior`, `Minibus_Cargo`,
    `Minibus_Wheels`.
  - Objects are named `GIT_Veh_Minibus_<Part>`. Materials are named `M_Minibus_*`.
- The v02 file also contains hidden helper collections (`MCP_Test`, `M3_Reference`,
  `Minibus__Cutters`, …). The renderers hide them.

### Module map (`tools/minibus/`)

- **`mb_lib.py`** — geometry library.
  - Core helpers:
    - `Builder` (bmesh wrapper)
    - `rbox`: chamfered quad lattice box
    - `tube` / `sweep` / `fillet_path` / `path_frames` / `circle_profile`
    - `lathe`
    - `thick_grid`, `thick_grid_holes`
    - `square_ring`
    - `clean_path`: keeps a path clear of the shell using a BVH
    - `quadify_ngons`, `finish_object`
  - Global flags:
    - `OPTIMIZE` (v05): no flat-face cuts; no chamfer on tiny boxes.
    - `LOD` (v06): fewer sides via `lod_sides`, coarser fillets, plain boxes, rivets dropped.
- **`mb_body.py`** — the body shell.
  - Structured quad lattice: rows × 19 columns, with window and door openings as missing faces, plus a Solidify modifier.
  - `configure(ridges, shape, groove, doors)`
  - `side_x_at(z)` gives the analytic side surface.
  - Ridge and groove rows: `RIDGE_UPPER_Z`, `RIDGE_LOWER_Z`.
- **`mb_parts.py`**
  - `Context` and materials.
  - Builds the body, fenders and wheels (loaded from the tyre file, holes capped, loose hub cap dropped, rim and rubber material split).
  - `cleanup`, `build_all`.
- **`mb_chassis.py`** — frame, axles and diffs, suspension (`coil()`; a sleeve under LOD), driveline and exhaust, wheel tubs.
- **`mb_front.py`** — bumper and bull bar, grille and headlights, hood plates, skid plate, shackles, mirrors, handles, rockers.
- **`mb_cage.py`** — exoskeleton laid out from shell creases (`clean_layout`, STANDOFF 0.24), roof rack, light bar, wing.
- **`mb_rear.py`** — rear bumper, tail lights, corner panels, exhaust stack, ladder, spare carrier.
- **`mb_interior.py`** — floor, dash, steering wheel, pedals and shifter, front seats, benches.
- **`mb_cargo.py`** — duffels, plaid bags, bundle, hard case, jerrycans.
- **`mb_decals.py`** — livery as geometry: bands and the "01" roundel. `build_lite` is the v05+ light version.
- **`mb_doors.py`** — sliding doors. Under LOD only the right door is built.
- **`mb_optimize.py`** — `cull_hidden` (removes faces hidden inside other solids), `planar_tris`, `lod_budget`.
- **`mb_fix_rims.py`** — patches the rim material split into an existing .blend.

## 6. Triangle counts (evaluated, with solidify)

- **v05:** 41,884 tris total.
- **v05_tris:** 37,802 tris total.
- **ClickUp parts:**

| Part | v05 | v05_tris |
|---|---|---|
| Livery decals | 398 | 322 |
| Roof rack | 496 | 496 |
| Luggage (9 objects) | 3,608 | 3,608 |
| Sliding doors (both) | 704 | 480 |
| **Sum** | **5,206** | **4,906** |

- **v05_tris by group:** interior 8,264; chassis 7,950; cage group 4,936; front 3,922;
  luggage 3,608; body group 3,570; rear 3,120; wheels 2,432.
- **v06:** 6,993 tris total.
  - Wheels kept their full 452 tris each. Collapse-decimating them ruined them; the tyre is already a minimal 12-sided mesh.

## 7. Bugs found and their status

- **The wheel rim material was never applied (v03 through v05).**
  - `mb_parts.build_wheels` called `me.materials.clear()` *after* writing faces, which reset every face to rubber.
  - Fixed in code: material slots are now set before `bm.to_mesh`.
  - Patched in place, at the user's explicit request, in `v05.blend` and `v05_tris.blend` with `mb_fix_rims.py`. Geometry is unchanged.
  - **`v05_StudioScenes.blend` (the team file) is NOT patched yet.** I offered to patch it; no answer yet. v03 and v04 also still have the bug, which is acceptable because they are historical.
- v04 files contain a duplicated hub-cap hexagon (z-fighting) in the wheels. Fixed from v05 on. The user knows.

## 8. Where things stand (latest conversation)

### ClickUp task

[Minibus final quality: livery, roof rack + luggage, open side door, <= 7k tris](https://app.clickup.com/t/123tp5xey2y)

- Status To Do, priority Urgent. The full text was shared as screenshots.
- Created by Ifeoluwa Ogunmuyiwa; assigned to the user by Jimoh Saheed.
- **Stage 2, driving prototype.** "Go to the BGMA file and access the Sedan car splits."
- The danfo should be split like the Roblox Sedan:

| Category | Mesh components | Gameplay purpose |
|---|---|---|
| Body Shell | Outer Frame, Black Stripe Layer | Paint-shop recolouring, base physics hull |
| Doors | Side Sliding Door, Rear Hatch | Cargo/passenger loading animations |
| Wheels | 4 independent wheels (Tire + Rim) | Vehicle physics, steering, rim customization |
| Steering | Steering Wheel | Luau rotation script |
| Lighting | Headlights, Taillights, Indicators | Dynamic braking, headlights, emissive materials. "Use Roblox Beam in the lights; copy what's used in the BGMA Sedan template." |
| Attachments | Roof Luggage Rack, Bull Bars | Vehicle upgrades, cargo capacity scaling |

The task also says:
- "All the other details you added will function as **layered details**, like layered
  clothing, so we can use one type of Danfo for all variants. Follow how the sedan was split."
- "Minibus blockout at correct scale **(18x8x9)**, separate wheels, pivot, hull, **Decal
  atlas v1 (512 px)**: danfo stripes, invented shop signs, number plate font."
- **Done when:** "Silhouette reads from behind and at 150 px; crew visible through door/windows."

**Sedan hierarchy in Roblox** (from screenshots):

```
Sedan (Model)
  Animations, BindableEvents, Constraints, Effects, Remotes, Scripts  (folders)
  Body (Model)
    FL       -> LF_wheel, LF_wheel_trim, tire
    FLdoor   -> LF_door, LF_door_glass, LF_door_int, LF_door_mirror
    FR       -> RF_wheel, RF_wheel_trim, tire
    FRdoor   -> RF_door, RF_door_glass, RF_door_int, RF_door_mirror
    RL       -> LR_wheel, LR_wheel_trim, tire
    RLdoor   -> LR_door, LR_door_glass, LR_door_int
    RR       -> RR_wheel, ...
  Chassis (Model)
```

The Sedan's Model has `LevelOfDetail = Automatic` and attributes such as
`AllowCarjacking`, `BaseEngineRPM 1745`, `BrakingTorque 90000` and `DrivingTorque 45000`.

### The user's latest position

Earlier the user said "I think we're still good with **v05**" (they had only read the
task heading). The 7k question was open until a voice note from a teammate settled it.

### Team voice note (2026-10-20), now the governing requirement

The note came from a teammate on Telegram, probably Jimoh or Ifeoluwa (not confirmed).
It was transcribed in the cloud session with faster-whisper `medium`, English forced:

> What I was trying to tell you was that the car, the model of the Danfo itself, the model
> of the Danfo should be like a normal Danfo model. Any of those details, maybe he sees a
> hazard kind of bus or a very dangerous kind of bus, all those other details should be
> added as layered detail. And everything entirely should be under 7k tris. I saw the
> tires you were doing, you don't really need that much vertices for the tire also. You
> don't even need that much at all. Well, I don't know, if you want me to send a car model
> from Synty to you, I can also send one so you can see. Can you send me the link, the
> drive link that Gideon sent to the group, so I can forward them to you?

Uncertain words: "Synty" (first pass heard "scinti"; Synty Studios makes low-poly game
assets) and the name "Gideon".

**What this settles:**

1. **The 7k limit is for the WHOLE vehicle.** v05 (41.9k) and v05_tris (37.8k) are far over.
   v06 hit 6,993 but by collapse-decimation, which the user found lost too much form.
   The right approach is to **model low-poly on purpose**, not to decimate.
2. **The base model is a plain, normal danfo**: body shell, doors, wheels, steering
   wheel, lights, glass.
3. **Everything else is a layered detail**, built as separate swappable parts so one base
   danfo serves every variant (e.g. a "hazard / dangerous bus" variant): exoskeleton cage,
   armour or riveted plates, bull bar, roof rack, luggage, light bar, wing, ladder, spare,
   exhaust stack, skid plate, shackles. Per the ClickUp task, the roof rack and bull bar
   are also "Attachments" (upgrades).
4. **The tyres must be much lighter.** The `ILikeTheTires.blend` tyre is 452 tris and
   can't be reduced cleanly (12-sided with tread lugs). Build a simple low-poly tyre and
   rim instead, split into separate tire and rim objects for rim customization. Ask the
   user before dropping the tyre style they chose.
5. The team may send a **Synty car model** as a poly-density reference, plus a Google
   Drive link. Ask the user for them before starting the low-poly build.

### Gaps between v05 and the full task

These were listed to the user. None has been started.

1. **Scale to 18×8×9 studs.**
   - Currently 18.9 × 9.6 × 12.1. Fitting the full height uniformly means a factor of about 0.741 (length drops to about 14).
   - About 0.81 if the rack, cargo and light bar don't count toward the height.
   - Needs a decision.
2. **Rear hatch** as a separate, hinged part. It's currently only a seam in the body.
3. **Wheels:** split each wheel into separate tire and rim (and trim) objects, with pivots at the hub, grouped FL/FR/RL/RR like the Sedan.
4. **Lights:** separate the headlight, tail-light and indicator lens meshes from the chrome surrounds for emissive materials, and add attachments for Roblox Beams.
5. **Glass:** add window and door glass parts (v05 has open holes) so the crew is visible through glass.
6. **Decal atlas, 512 px:**
   - UV-map the body.
   - Make a texture with danfo stripes, invented shop signs and a number-plate font.
   - Today the livery is geometry, which suits the "Black Stripe Layer" but has no UVs.
7. **Hierarchy and naming:**
   - Rename and group to mirror the Sedan (Body / FL / FLdoor / … / Chassis).
   - Put each pivot in the right place (wheels at the hub, sliding door on its track, hatch at its hinge, steering wheel on its column axis).
   - Attachments (rack, bull bar) and layered details (cage, ladder, spare, cargo…) go as separate groups.
8. **Open side door state** for the "open side door" requirement. Options:
   - Slide the left door back along its track: it must clear the rear fender flare and stay inside the cage standoff.
   - Animate it in Roblox. v06 simply removed the left door.

### Unfinished work in the code

- `v06quad` variant (in `mb_build.py`): the user asked for a "v06quadvar" (LOD but predominantly quads and keeping more form), then said "scratch that".
  - **Do not continue it unless asked again.**
  - With LOD geometry and no decimation it came to ~16.4k tris before planar.
- The scratch `.blend` outputs from the old session are gone. Only files committed to git exist.

## 9. Suggested next step

Ask or confirm with the user before big work. Likely next request: a **v07 game
model** that meets the voice note and the ClickUp task:

- A purpose-built low-poly base danfo, **≤7k tris for everything including the layers**.
  Use v05 as the shape and proportion reference, scaled to 18×8×9.
- Layered-detail parts kept separate.
- The Roblox split and hierarchy (§8 gaps 1–5, 7, 8).
- Possibly the decal atlas (§8 gap 6).
- Predominantly quads, tris where needed (the user's stated preference).
- Ask for the Synty reference first.

Rules for v07:

- **New file.** Leave v05 untouched.
- **Add a variant** in `mb_build.py`, or a post-process script that opens v05 and re-organises it.
- **Render all sides** and show contact sheets.
- **Commit and push** to `claude/minibus-v03`, ending each commit message with:

```
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_0183KFnxyf98YUY2dBikCWQ8
```

(Use the attribution lines your own session gives you, if different.)
