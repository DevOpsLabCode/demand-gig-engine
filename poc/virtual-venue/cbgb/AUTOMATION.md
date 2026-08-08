# CBGB Historical Twin — Automated Pipeline

The target operating model is **one automated pipeline with explicit policy gates**.

The system should not depend on a researcher manually moving files between tools. Discovery, deduplication, rights classification, evidence normalization, reconstruction job creation, QA, packaging and publication should all be machine-driven.

The only steps that remain human-authorized are the steps software cannot legitimately decide for us:

1. accepting/licensing rights from a third party;
2. obtaining permission for a physical survey;
3. approving unresolved historical interpretations;
4. authorizing public/commercial publication.

Those are not manual implementation steps. They are **approval events**. The pipeline pauses, records the gate, and resumes automatically when approval arrives.

## One-command POC

```bash
cd poc/virtual-venue/cbgb
python3 run_pipeline.py
```

That automatically:

1. validates the seed evidence pack;
2. discovers Wikimedia Commons CBGB assets;
3. downloads only current allow-listed open image candidates;
4. creates discovery + attribution manifests;
5. collects broad public metadata from MusicBrainz, Library of Congress, Internet Archive and Wikidata;
6. harvests CBGB catalog occurrences from the NYU Fales MSS.213 and MSS.305 finding aids without downloading restricted media;
7. validates the evidence pack again;
8. hashes core evidence inputs;
9. writes `pipeline-run.json` with the complete run state.

With a permissioned capture:

```bash
python3 run_pipeline.py \
  --capture ./capture/cbgb-current/ \
  --approved-rights
```

The pipeline then calls the existing reconstruction process:

```text
capture
  -> Nerfstudio/COLMAP processing
  -> Splatfacto training
  -> PLY export
  -> PlayCanvas SOG
```

The POC will not publish automatically merely because reconstruction succeeded. Publication needs an explicit gate:

```bash
python3 run_pipeline.py \
  --capture ./capture/cbgb-current/ \
  --approved-rights \
  --approved-publish
```

In the isolated POC branch this only marks the build as `ready_for_external_publisher`; it intentionally does **not** write to production infrastructure or merge anything into `main`.

## Production target architecture

```text
                         EVENT SOURCES
                              |
       +----------------------+----------------------+
       |                      |                      |
  scheduled crawl        venue upload          archive update
       |                      |                      |
       +----------------------+----------------------+
                              |
                              v
                       INGEST ORCHESTRATOR
                              |
             +----------------+----------------+
             |                |                |
             v                v                v
       SOURCE DISCOVERY   CAPTURE INGEST   PARTNER INGEST
             |                |                |
             +----------------+----------------+
                              |
                              v
                       PROVENANCE NORMALIZER
                              |
                   content hash / dedupe
                              |
                              v
                         RIGHTS ENGINE
                              |
              +---------------+---------------+
              |               |               |
              v               v               v
           A/B/C              D               E
        usable input     metadata only      reject
              |               |               |
              +-------+-------+               |
                      |                       |
                      v                       v
                  EVIDENCE GRAPH        audit record
                      |
             +--------+--------+
             |                 |
             v                 v
        TIME RESOLVER     CONFLICT ENGINE
             |                 |
             +--------+--------+
                      |
                      v
                GEOMETRY SOLVER
                      |
             confidence / gaps
                      |
          +-----------+------------+
          |                        |
          v                        v
    sufficient data           gap detected
          |                        |
          |                        v
          |                  CAPTURE MISSION
          |                        |
          +-----------<------------+
                      |
                      v
              RECONSTRUCTION JOB
                      |
        +-------------+-------------+
        |                           |
        v                           v
    SPLAT/MESH                   GAME MESH
        |                    navmesh / anchors
        +-------------+-------------+
                      |
                      v
                  AUTO QA
                      |
          geometry / performance /
          attribution / provenance
                      |
             +--------+--------+
             |                 |
             v                 v
           pass              fail
             |                 |
             |                 v
             |             retry/task
             |
             v
              HISTORICAL REVIEW GATE
                      |
                      v
                   PACKAGE
                      |
                      v
                 PUBLISH GATE
                      |
                      v
              CDN / LIVE WORLD
```

## Automated stages

### 1. Discovery

Scheduled workers repeatedly query approved sources and archive catalogs.

Every result becomes a `SourceCandidate` containing:

- source URL/catalog ID;
- discovered timestamp;
- creator/institution;
- media type;
- date/date range;
- possible place/event relationships;
- source-specific rights metadata;
- content URL only where collection is permitted.

Nothing goes directly into reconstruction.

### 2. Rights classification

The rights engine assigns A/B/C/D/E and a machine-readable reason.

Examples:

```text
CC BY 2.0 image
 -> C
 -> download candidate
 -> attribution required
 -> derivative allowed

NYU Fales archival reel
 -> D
 -> catalog metadata only
 -> permission required for reproduction

Google Street View image
 -> E for reconstruction
 -> never download/derive production model from it
```

Ambiguous licenses default to **D**, never to C.

### 3. Deduplication

For legally downloadable content calculate:

- SHA-256;
- perceptual image hash;
- EXIF identity;
- source URL identity;
- near-duplicate image embedding;
- timestamp/camera grouping.

This prevents the same historical image appearing through five websites from becoming five independent pieces of evidence.

### 4. Evidence extraction

The engine produces observations such as:

```text
object: stage-left-front
state: cbgb-1979
observation: visible below ceiling fixture F12
source: NYU reel 305.xxxx
confidence: 0.78
media copied into model: false
```

For reusable imagery, computer vision can also extract feature points and camera candidates.

For reference-only copyrighted media, production policy should limit automated extraction to what the access/license permits. Otherwise a researcher records observations manually and the media itself stays outside the reconstruction store.

### 5. Temporal resolution

Every observation is assigned a historical validity range.

The engine should never use:

```text
2009 fixture -> automatically true in 1975
```

Instead it asks whether the object is:

- verified persistent;
- period-specific;
- probable;
- unknown;
- contradicted.

### 6. Conflict engine

Conflicts become tasks rather than being overwritten.

Example:

```text
315 Bowery
317 Bowery
313 Gallery
```

The system records all three and creates:

```text
ResearchTask:
  resolve historical address / tenant-space relationship
  priority: high
  evidence: [Cornell flyer A, flyer B, official history, DOB plan]
```

### 7. Automated geometry scoring

The geometry engine computes coverage for anchors:

```text
entrance             0.94
bar start            0.91
bar end              0.78
stage center         0.89
stage width          0.66
rear transition      0.52
bathroom route       0.41
ceiling height       0.32
```

If confidence is below the configured threshold, the system creates a gap mission automatically.

### 8. Capture mission generation

Example generated task:

```text
Mission: CBGB-315-CEILING-001
Need:
  ceiling-to-floor measurement
  12 photographs
  three viewpoints
  known-length marker
Location:
  current 315 Bowery interior
Rights:
  venue permission required
Reward/status:
  configurable
```

For an operating venue, the venue onboarding app can generate these tasks while the owner is scanning.

### 9. Reconstruction

Once coverage and rights policy pass:

- select only approved reconstruction inputs;
- generate immutable input manifest;
- launch GPU job;
- create splat/mesh;
- generate simplified collision geometry;
- solve stage/seat/door anchors;
- store all derived-asset provenance.

Each output records the exact hashes and evidence IDs used to create it.

### 10. Automated QA

QA should include:

- missing texture/asset checks;
- geometric holes;
- scale sanity;
- entrance/stage/bar anchor existence;
- camera reprojection error;
- performance/FPS budget;
- `.sog` size budget;
- browser smoke test;
- attribution completeness;
- prohibited-source check;
- historical-state contamination check;
- broken evidence URLs/catalog IDs;
- confidence threshold checks.

A failed check creates a retry or research task automatically.

### 11. Historical review gate

The system can automate confidence scoring but cannot truthfully decide a contested historical interpretation by itself.

So this becomes a workflow state:

```text
WAITING_HISTORICAL_APPROVAL
```

The reviewer sees only unresolved/high-impact issues and approves/rejects them. Once approved, the workflow resumes without manual file movement.

### 12. Publication gate

Before publication the automated compliance report must show:

```text
prohibited source inputs: 0
unresolved rights: 0
missing attribution: 0
critical geometry below threshold: 0
historical-review gate: approved
performance test: passed
```

Then an explicit publication approval can release the immutable package.

## AWS implementation target

This fits the existing AWS direction well.

A production implementation can use:

- S3 — immutable evidence/capture/derived-asset stores;
- EventBridge — scheduled discovery and event routing;
- SQS — ingestion/reconstruction/QA queues;
- Step Functions — state machine and approval waits;
- ECS/Fargate — metadata collectors, parsers, QA and CPU jobs;
- GPU ECS/EC2 or AWS Batch — Nerfstudio/Splatfacto reconstruction;
- RDS PostgreSQL — evidence graph metadata, state, rights and tasks;
- Redis — short-lived job/session state where useful;
- Lambda — lightweight event handlers and manifest validation;
- CloudWatch/X-Ray — pipeline observability;
- KMS — encryption;
- S3/CloudFront — versioned browser-ready twin assets;
- SNS/SES or application notifications — approval/action requests.

The production state machine should use idempotent stage IDs so every task can safely retry.

## Required state-machine statuses

```text
DISCOVERED
METADATA_NORMALIZED
RIGHTS_CLASSIFIED
BLOCKED_RIGHTS
READY_FOR_INGEST
INGESTED
EVIDENCE_EXTRACTED
CONFLICTS_OPEN
GEOMETRY_INCOMPLETE
CAPTURE_REQUIRED
READY_FOR_RECONSTRUCTION
RECONSTRUCTING
RECONSTRUCTED
QA_FAILED
QA_PASSED
WAITING_HISTORICAL_APPROVAL
HISTORICAL_APPROVED
WAITING_PUBLISH_APPROVAL
PUBLISHED
SUPERSEDED
```

## Immutability

Never silently replace a historical twin.

Publish:

```text
cbgb-2006-closing/v0.1.0
cbgb-2006-closing/v0.2.0
cbgb-2006-closing/v1.0.0
```

Each version gets:

- build manifest;
- evidence snapshot hash;
- source-license manifest;
- reconstruction settings;
- model hash;
- QA report;
- approvals;
- supersedes/superseded-by links.

## What “100% automated” means here

The **workflow** can be 100% automated: it discovers, classifies, queues, waits, retries, reconstructs, tests, packages and publishes without people moving files or running individual commands.

The **decisions that require legal permission or historical judgment should not be faked as automatic**. They are explicit gates inside the automated workflow. Once a human/partner supplies the decision, the system resumes automatically.

That model is scalable from CBGB to Bleecker/MacDougal and eventually to thousands of venues and historical cultural corridors.
