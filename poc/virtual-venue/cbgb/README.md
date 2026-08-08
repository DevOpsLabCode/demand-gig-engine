# CBGB Historical Twin POC

This folder is the historical-reconstruction test case for the Open Concert Reality Evidence Engine.

The target is the former CBGB & OMFUG club at 315 Bowery, New York. Unlike the first generic virtual-room POC, this case is deliberately difficult: the club closed in 2006, so we must reconstruct a specific historical state from surviving evidence while keeping licensing and uncertainty explicit.

## What is already known with high confidence

The Bowery Historic District National Register documentation identifies 313-315 Bowery as two 1878 tenement buildings joined in 1934 into a four-story, four-bay lodging house with a modest Art Deco facade. It documents the Palace Bar/Hotel history, Hilly Kristal's lease of the ground-floor bar, CBGB's 1973-2006 operation, retention of the original bar/fixtures, and says the club interior was largely preserved after closure.

Wikimedia Commons also has a 12-image 2009 interior category. Individual examples such as `CBGB 2009 Interior.jpg` and `CBGB 2009 Display stage.jpg` are CC BY 2.0. Other CBGB Commons images use a mix of CC BY/CC BY-SA/public-domain licenses. We do **not** assume an entire category has one license; the collector verifies file metadata individually.

## Files

- `evidence.json` — curated evidence and rights/provenance classes.
- `geometry.json` — high-confidence building/club facts plus explicitly marked estimates.
- `collect_open_assets.py` — Wikimedia Commons collector that downloads only allow-listed open-licensed files and writes attribution metadata.
- `CAPTURE_GAPS.md` — measurements, current-capture work and historical evidence still needed.

## Collect the reusable seed images

From this directory:

```bash
python3 collect_open_assets.py ./open-assets
```

The script uses the Wikimedia Commons API, examines per-file license metadata, downloads only open/public-domain candidates, and writes:

```text
open-assets/
  <downloaded images>
  attribution.json
```

`attribution.json` is part of the asset chain of custody. Do not delete it after reconstruction.

## Important rights rule

The reconstruction input set is **not** "everything we can see online." It is everything we can legally reuse plus our own/partner captures.

Examples:

- Wikimedia CC BY/CC BY-SA/public-domain material: candidate reconstruction input, subject to exact license terms.
- Project-owned current capture: preferred reconstruction input.
- NYPL copyrighted photographs: reference graph only unless permission is obtained.
- Cornell punk-flyer scans: reference graph only unless commercial reuse permission is obtained.
- Magazine/news/photographer sites: reference graph only unless separately licensed.
- Google Maps/Street View: do not scrape or derive the production 3D asset from it.

Reference-only evidence is still useful. It can confirm that an object existed, help date a wall/sign/stage configuration, suggest camera positions, identify performers/events, and expose contradictions that require more research. It just must not silently become a commercial texture/training asset.

## Proposed reconstruction workflow

```text
OPEN/OWNED IMAGES -----------+
CURRENT PERMISSIONED SCAN ---+--> pose solving / photogrammetry
PARTNER ARCHIVE -------------+              |
                                            v
REFERENCE-ONLY GRAPH --> feature checks --> base geometry
                                            |
                                            v
                                 historical-state modeling
                                            |
                            +---------------+----------------+
                            |                                |
                      visual reality                    game layer
                 splat / mesh / textures          collision / seats / stage
                            |                                |
                            +---------------+----------------+
                                            |
                                            v
                                  CBGB historical twin
```

## Historical states, not one blended room

Do not blend evidence from 1975 and 2005 into one supposedly exact room. The engine should eventually support versions such as:

- `cbgb-1975`
- `cbgb-1979`
- `cbgb-1985`
- `cbgb-1995`
- `cbgb-2006-closing`

A shared base geometry can be reused where evidence supports it, while posters, paint, fixtures, equipment, signage and event content vary by time state.

## First POC state

Start with a **late-club / closing-era reconstruction** because the evidence density is much better than for 1973-1975. Use open 2005 exterior/stage photos and the 2009 preserved-interior set to solve the room, then verify which post-closure details differ from the 2006 club.

Once the geometry is stable, work backwards to 1970s states using period photographs, flyers, interviews and licensed archives.

## Definition of done for CBGB POC v0

1. Open-assets collector produces a rights manifest with every downloaded image.
2. Base room proportions are reconstructed with visible confidence annotations.
3. Entrance, bar, stage and rear-room anchors are positioned.
4. At least one browser-walkable historical state is available.
5. A synthetic/licensed performance video can play on the reconstructed stage.
6. Every nontrivial historical feature is traceable to one or more evidence IDs.
7. Uncertain features are labeled estimated rather than presented as fact.

This POC is a historical reconstruction research project, not an assertion that the first model is a perfect replica. Accuracy should improve as measurements, permissions and archival evidence are added.
