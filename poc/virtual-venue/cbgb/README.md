# CBGB Historical Digital Twin POC

This folder is the first **lost/historical venue** test case for the Open Concert Reality Evidence Engine.

The target is the former CBGB & OMFUG club at 315 Bowery, New York. The point of this POC is deliberately harder than scanning a venue that still operates: CBGB closed in 2006, so the engine must reconstruct a specific historical state from surviving building fabric, open images, archival catalogs, flyers, video references, government records, oral histories and permissioned captures while keeping provenance, time and rights explicit.

**Nothing in this folder should be merged into `main` until the POC is manually tested and approved.**

## POC thesis

A historical digital twin is not a 3D artist's impression. It is:

```text
GEOMETRY TRUTH
  + REUSABLE VISUAL EVIDENCE
  + REFERENCE-ONLY HISTORICAL OBSERVATIONS
  + EVENT / ARTIST METADATA
  + RIGHTS / PROVENANCE
  + CONFIDENCE
  + TIME STATE
          |
          v
HISTORICAL DIGITAL TWIN
```

Every important rendered feature should ultimately answer:

- what is it?;
- where was it?;
- when was it valid?;
- which sources support it?;
- how confident are we?;
- which actual pixels/models are we legally allowed to redistribute?;
- which sources were used only as research references?

## Best evidence discovered so far

### 1. National Register / preservation record

The Bowery Historic District National Register documentation identifies 313-315 Bowery as two 1878 tenement buildings joined/altered in 1934 into a four-story, four-bay lodging-house resource with a modest Art Deco facade. It documents the Palace Bar/Hotel history, Hilly Kristal's lease, CBGB's 1973-2006 operation, retention of the original bar/fixtures, and says the club interior was largely preserved after closure.

It also cites a potentially critical unpublished 2006 report by Lisa Kersavage and Marci Reaven, *Historical documentation of 313-315 Bowery*. Obtaining that report is Priority 0.

### 2. Current building identity / surviving fabric

NYC DOB data identifies the parcel as BBL `1004570005`, BIN `1006536`. John Varvatos still lists a store at 315 Bowery. Because preservation records say the post-CBGB conversion retained substantial interior fabric, a permissioned current survey is our best route to a metric base shell.

The exact historic CBGB tenant footprint remains **UNSOLVED**. The old 25×75 ft placeholder has been explicitly deprecated as geometry truth.

### 3. Wikimedia Commons open seed corpus

Commons exposes a 12-image 2009 interior category plus a broader CBGB category. Some files are CC BY, some CC BY-SA/GFDL, some public domain and others may differ. The collector never assumes category-wide licensing.

Especially valuable items include a 1975 Metropolis Video photograph, 2004-2005 facade/stage/toilet views, public-domain post-closure imagery and the 2009 preserved-interior set.

### 4. NYU Fales NIGHTCLUBBING archive

The Pat Ivers / Emily Armstrong NIGHTCLUBBING archive is a major spatial-reconstruction lead. It contains a large body of 1975-1980 downtown-club video and many specifically identified CBGB reels: Dead Boys, the 1978 Blitz Benefit, backstage/interview/bathroom ambience, Voidoids, Only Ones, Revelons, Bad Brains and more.

NYU explicitly says copyright/publicity/privacy rights were not transferred. These recordings are therefore **reference-only until permission/licensing is secured**. Their catalog metadata and human-created geometry observations can still guide research without copying the video into the production model.

### 5. Cornell Punk Flyers / address variants

Cornell provides high-value event chronology, including a 1974 CBGB flyer at 315 Bowery and later CBGB flyer records reported at 317 Bowery. Do not normalize those away. They may help solve how the later CBGB/CB's 313 Gallery/adjacent spaces were addressed and connected.

### 6. CB's 313 Gallery

Official CBGB history says a record store was replaced in the late 1980s by the second performance/art space `CB's 313 Gallery`. This means later CBGB was not always a single simple room. The POC must distinguish the main 315 club, 313 Gallery, basement/adjacent spaces and any changing connections between them.

## Files

### Core research

- `evidence.json` — curated source registry, rights classes, provenance and research observations.
- `geometry.json` — building/parcel facts, shell clues, unsolved tenant footprint, geometry hypotheses and camera-solve strategy.
- `FOOTPRINT_RESEARCH.md` — deep research plan and phased reconstruction strategy.
- `EVIDENCE_GRAPH.md` — graph schema for sources, observations, camera poses, objects, states, events and licenses.
- `CAPTURE_GAPS.md` — live gap register for measurements, plans, archive access and physical captures.
- `timeline_seed.csv` — evidence-backed seed chronology; deliberately preserves source address/date conflicts.
- `reference_catalog_seed.json` — specific NYU/Cornell/Commons reference records and spatial-value ranking.
- `RIGHTS_ACQUISITION_QUEUE.csv` — prioritized access/licensing/outreach targets.

### Collectors / validation

- `collect_open_assets.py` — discovers all files in selected Wikimedia Commons CBGB categories, records every result, and downloads only allow-listed open image candidates.
- `collect_public_metadata.py` — metadata-only broad-recall collector for MusicBrainz, Library of Congress, Internet Archive and Wikidata. It downloads no linked media.
- `validate_poc.py` — validates JSON/CSV integrity, rights classes, evidence IDs, confidence values and critical research invariants.

## Rights model

### A — owned

Project-created or contracted capture. Preferred.

### B — partner licensed

Media/scan supplied under explicit commercial derivative rights.

### C — open/public domain

Candidate reconstruction input subject to exact per-item license, attribution and share-alike requirements.

### D — reference only

Keep metadata, catalog IDs, links and permitted human research observations. Do not silently use the source media itself as a commercial texture/training input.

### E — prohibited/restricted derivative source

Do not scrape, bypass access controls or create production derived assets contrary to source terms. Google Maps/Street View is explicitly not a production reconstruction source.

## Run the open-image discovery collector

From this directory:

```bash
python3 collect_open_assets.py ./open-assets
```

It produces:

```text
open-assets/
  <downloaded allow-listed image candidates>
  discovered.json
  attribution.json
```

`discovered.json` includes **all Commons files found**, including metadata-only/rejected candidates and the reason they were not downloaded.

`attribution.json` contains the current downloaded subset, creator/license/source metadata and SHA-256 hashes.

Discovery/download status is not a permanent rights guarantee. Re-review item licenses before any public/commercial release.

## Run broad public metadata discovery

```bash
python3 collect_public_metadata.py ./discovered-public-metadata.json
```

This queries public metadata/search endpoints and stores research leads without copying the underlying media. It currently includes:

- MusicBrainz events associated with the CBGB place MBID;
- Library of Congress search results for CBGB / 313 / 315 Bowery;
- Internet Archive metadata candidates;
- Wikidata entity metadata.

A returned record is a **lead, not a rights grant and not automatically a historical fact**.

## Validate the evidence pack

```bash
python3 validate_poc.py
```

The validator checks at least:

- JSON parses;
- required A-E rights classes;
- duplicate source IDs;
- timeline source references;
- timeline/confidence values;
- URL shape;
- critical archive/current-survey source presence;
- old 25×75 estimate remains deprecated;
- historic tenant footprint remains `UNSOLVED` until better evidence exists.

## Reconstruction pipeline

```text
                    REALITY EVIDENCE GRAPH
                             |
          +------------------+------------------+
          |                  |                  |
     OWNED / B          OPEN / C          REFERENCE / D
    scans/media       reusable files       archive leads
          |                  |                  |
          +---------+--------+             observations
                    |                           |
                    v                           v
              METRIC BASE SHELL <-------- CAMERA SOLVES
                    |
             HISTORICAL STATES
                    |
        +-----------+------------+
        |                        |
   VISUAL LAYER             GAME LAYER
 mesh/splat/textures    collision/seats/stage
        |                        |
        +-----------+------------+
                    |
              LIVE / ARCHIVE MEDIA
                    |
                 COMMERCE
```

## Historical states

Do not blend decades. Initial state families:

- `pre-cbgb-palace-bar`
- `cbgb-1973-1976`
- `cbgb-1977-1982`
- `cbgb-1983-1989`
- `cbgb-1990-1999`
- `cbgb-2000-2005`
- `cbgb-2006-closing`
- `post-cbgb-2008-2009-preserved-retail`
- `current-surviving-fabric`

The first browser state should still be **`cbgb-2006-closing`**, because late-club/post-closure evidence density is highest. Then roll backward using period evidence.

## Camera solving from restricted archives

A copyrighted archival reel can be useful without becoming a copied production asset.

Research process:

1. researcher views permitted archive material;
2. records timecode and visible fixed features;
3. maps homologous points to our shell;
4. estimates camera pose/FOV;
5. stores only the observation/pose/evidence reference unless broader rights exist;
6. combines many independent poses to constrain stage/bar/walls;
7. uses owned/open/licensed assets to render the final production scene.

This distinction is central to the POC.

## CBGB + CB's 313 Gallery spatial problem

Treat the later complex as a graph, not one rectangular box:

```text
BOWERY
  |
  +-- 313 storefront / Record Canteen -> later CB's 313 Gallery
  |       |
  |       +-- ground-floor performance/gallery area
  |       +-- basement / secondary-space evidence to solve
  |
  +-- 315 storefront / main CBGB room
          |
          +-- entrance
          +-- historic bar
          +-- main floor
          +-- stage
          +-- rear/backstage/bathroom-stair relationships
```

Exact doors/connections/time changes are currently unresolved.

## Browser POC features to add next

1. `cbgb-2006-closing` placeholder shell using **only clearly marked estimated geometry** until a proper survey/plan solve exists.
2. Evidence/debug mode: click stage/bar/door and see confidence + source IDs.
3. Historical year/state selector.
4. Load reusable Commons imagery as registered reference planes/feature markers.
5. Use the generated copyright-safe POC performance video on the virtual stage.
6. Preserve the existing WASD/seat navigation layer.
7. Later replace placeholder shell with current-survey/plan/camera-solved geometry.

## Definition of done — CBGB POC v0

The POC is successful when all of these are true:

1. open-asset collector produces discovery + attribution manifests;
2. broad metadata collector produces searchable discovery records;
3. evidence pack passes `validate_poc.py`;
4. a browser user can enter a CBGB closing-era reconstruction;
5. entrance, bar, stage and rear-area anchors carry evidence/confidence values;
6. synthetic/licensed performance video plays on the stage;
7. debug mode exposes provenance for nontrivial historical features;
8. timeline/state changes can alter at least signage/posters/fixture state without blending periods;
9. reference-only copyrighted media is never an undocumented model/texture input;
10. the exact same evidence-engine pattern can be reused for a second historical venue.

## What the POC must never claim yet

- that the current model is an exact measured replica;
- that the full club was 25×75 ft;
- that 313/315/317 address references are already resolved;
- that a 2009 preserved-retail object necessarily existed in 1975;
- that a publicly viewable photo/video is automatically licensed for our commercial reconstruction;
- that a community memory is a measured fact.

The public experience should be labeled **Historical Reconstruction** until the evidence warrants stronger language.
