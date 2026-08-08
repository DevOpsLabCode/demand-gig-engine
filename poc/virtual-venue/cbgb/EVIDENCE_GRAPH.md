# CBGB Reality Evidence Graph

The POC needs more than an asset folder. It needs a graph that can answer **what do we think existed, where, when, why, based on which evidence, and are we allowed to render it?**

## Core node types

### `Place`

Examples: CBGB, Palace Bar, 313-315 Bowery, CB's Gallery, Bowery streetscape.

Required fields:

- stable ID;
- canonical name;
- aliases;
- reported addresses;
- coordinates when supported;
- valid date range;
- parent/adjacent places;
- evidence IDs.

### `HistoricalState`

Examples: `cbgb-1975`, `cbgb-1979`, `cbgb-2006-closing`.

Fields:

- state ID;
- date/date range;
- geometry version;
- object-set version;
- facade/signage version;
- confidence summary;
- evidence cutoff date.

### `Zone`

Examples: entrance, main room, bar, stage, backstage/rear, bathroom/stair area, adjacent gallery.

Fields:

- local coordinate frame;
- valid date range;
- geometry confidence;
- parent Place/State.

### `Object`

Examples: historic bar, stage, doorway, column, ceiling fixture, sign, poster, speaker, toilet fixture.

Fields:

- position/rotation/scale;
- dimensions and units;
- valid date range;
- persistence classification;
- appearance asset IDs;
- position/dimension/appearance confidence;
- rights status.

### `EvidenceSource`

Examples: National Register PDF, NYU MSS.305, Commons category, Cornell item, photographer archive.

Fields:

- creator/institution;
- title;
- URL/catalog ID;
- rights class;
- license/rights note;
- date accessed;
- source reliability;
- collection restrictions.

### `EvidenceItem`

Examples: one photo, one video reel, one flyer, one plan sheet, one oral-history segment.

Fields:

- source ID;
- item ID/catalog ID;
- capture/creation date;
- creator;
- media type;
- reported venue/address;
- rights class;
- download/copy permission;
- hash if legally stored;
- local path only if permitted;
- visible-feature observations.

### `Observation`

This is the key separation between copyrighted evidence and our reconstruction facts.

Example:

```json
{
  "id": "obs-1978-000184",
  "source_item": "nyu-mss305-305.0006",
  "historical_state": "cbgb-1978",
  "observer": "researcher-or-approved-vision-pipeline",
  "claim": "stage left corner aligns below ceiling fixture F-12",
  "geometry_target": "stage-left-front",
  "confidence": 0.78,
  "media_copied_into_model": false
}
```

Reference-only copyrighted media can support an `Observation` without becoming a redistributed texture/training file.

### `CameraPose`

Fields:

- evidence item/frame/timecode;
- camera origin/orientation;
- approximate focal length/FOV;
- reprojection error;
- homologous feature IDs;
- pose confidence;
- historical state.

Repeated poses from independent sources allow us to solve room dimensions and feature positions.

### `Event`

Fields:

- date/time;
- performers;
- billing;
- venue/place;
- reported address;
- flyer IDs;
- recording IDs;
- setlist references;
- source conflicts;
- event confidence.

### `PersonOrBand`

Used only for public cultural/event relationships, not private profiling.

Fields:

- canonical name;
- external IDs (MusicBrainz/Wikidata when available);
- event relationships;
- archive/source relationships.

### `LicenseRecord`

Fields:

- rights class A/B/C/D/E;
- exact license identifier;
- attribution required;
- share-alike flag;
- commercial use allowed;
- derivatives allowed;
- model-training permission if separately relevant;
- source URL;
- review date;
- reviewer/status.

### `DerivedAsset`

Examples: splat, mesh, material, texture atlas, navmesh, stage plane.

Fields:

- source evidence IDs;
- derivation steps;
- content hashes;
- applicable licenses;
- public redistribution status;
- historical state;
- confidence.

## Graph edges

Recommended relationships:

- `LOCATED_IN`
- `ADJACENT_TO`
- `PART_OF`
- `VALID_DURING`
- `PRECEDES`
- `SUCCEEDS`
- `DEPICTS`
- `OBSERVES`
- `CORROBORATES`
- `CONTRADICTS`
- `CAMERA_POSE_FOR`
- `FEATURE_MATCHES`
- `DERIVED_FROM`
- `LICENSED_BY`
- `CREATED_BY`
- `PERFORMED_AT`
- `OCCURRED_AT`
- `HAS_FLYER`
- `HAS_RECORDING`
- `HAS_SETLIST`
- `REQUIRES_PERMISSION_FROM`
- `SUPERSEDES_GEOMETRY`

## Confidence model

Do not hide uncertainty inside a single number. Track at least:

```text
geometry.position
geometry.dimension
appearance
historical_date
source_identity
rights
```

Suggested thresholds:

- `>= 0.90` verified/high confidence;
- `0.75-0.89` strong reconstruction;
- `0.50-0.74` plausible but unresolved;
- `< 0.50` placeholder/hypothesis.

## Conflict handling

Never overwrite conflicting evidence. Example:

```text
source A says: 315 Bowery
source B flyer says: 317 Bowery
```

Store both `reported_address` observations, connect them to the same event/place candidate with independent confidence, and create a research task to resolve whether the later CBGB/CB's complex included adjacent numbered space.

Likewise, modern administrative records that say `year built: 1920` do not erase preservation documentation showing 1878 construction and a major 1934 alteration. The graph stores both with source context and assigns the historical interpretation to the better-documented source.

## Provenance rule for rendered objects

Every nontrivial rendered object should be queryable like:

```text
Stage, CBGB 1979
  position confidence: 0.91
  dimensions confidence: 0.76
  appearance confidence: 0.69
  evidence:
    - Commons open photo A
    - NYU video observations 305.xxxx
    - current-survey anchor S-17
  rendered pixels derived from:
    - project-owned texture capture
    - CC BY asset X
  reference-only sources used for checks:
    - NYU reel Y
  valid during:
    - 1977-1980
```

## POC UI implication

Add a research/debug toggle to the browser twin. Clicking any reconstructed object should show:

- what it is;
- which historical state it belongs to;
- confidence bars;
- evidence count;
- reusable vs reference-only source count;
- what is estimated;
- source/attribution links when publication rights permit.

The public entertainment view can hide technical clutter, but the evidence graph remains behind every scene.
