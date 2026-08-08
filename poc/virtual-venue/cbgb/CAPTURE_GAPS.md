# CBGB reconstruction capture and evidence gaps

The research corpus is now large enough to build a serious historical POC, but it is **not** yet enough to claim a metrically exact CBGB room. This document is the gap register: anything unresolved stays visible here until measured, licensed or corroborated.

## Priority 0 — recover the 2006 preservation research

The Bowery National Register report cites:

> Lisa Kersavage and Marci Reaven, *Historical documentation of 313-315 Bowery*, July 24, 2006, unpublished letter report to the Landmarks Preservation Commission from Municipal Art Society / Place Matters.

This may be the most important unpublished source because it was prepared while CBGB was still operating/closing and fed directly into later preservation documentation.

Tasks:

- locate a complete copy;
- determine whether drawings, photographs, measurements or fixture descriptions accompany it;
- record page/item-level provenance;
- obtain permission for any media we want to display or derive assets from.

## Priority 0 — permissioned current 315 Bowery survey

The National Register documentation says the post-CBGB commercial tenant largely preserved the club interior. John Varvatos currently lists a Bowery store at 315 Bowery. A permission-based current capture is therefore the best potential route to recover the physical shell.

Capture if permission is granted:

- full 360-degree or normal-video walk from entrance to rear and back;
- slow perimeter pass at approximately eye height;
- second pass around 1.0-1.2 m camera height;
- LiDAR/depth capture where device capability permits;
- front facade straight-on and ±15/30/45 degree angles;
- entrance/storefront corners with measuring references;
- surviving historic bar from multiple angles, if still present;
- stage/floor area corresponding to historic stage location;
- ceiling, floor transitions, columns, beams and structural offsets;
- doorways, stairs, basement access and bathroom routes only where permission allows;
- adjoining wall relationship to 313 Bowery;
- laser measurements for a minimal control network;
- AprilTag/known-length reference board in several frames.

Do not enter private, staff-only, mechanical, residential or service spaces without explicit permission. Blur bystanders, payment screens, personal information and security-sensitive details before any dataset is published.

## Priority 1 — solve the actual historic CBGB tenant footprint

We now know the full parcel/building envelope much better than before, but **the club footprint itself remains unsolved**.

Known/secondary shell clues:

- NYC identity: BBL `1004570005`, BIN `1006536`;
- full parcel/building secondary records: about 50.92×166 ft lot and 51×162 ft building;
- Acadia retail brochure: about 40 ft Bowery frontage for the marketed 313-315 retail property;
- former 25×75 POC estimate: deprecated, not geometry truth.

Still needed:

- exact 315 storefront width;
- exact historic entrance width/offset;
- main-room clear width at front/middle/rear;
- front door to bar start/end distances;
- front door to stage plane;
- stage width/depth/height by period;
- stage to rear-wall/backstage transition;
- ceiling height and changes;
- bar face/back-bar geometry;
- column/beam/wall offsets;
- basement stair/bathroom geometry;
- whether/how internal openings between 313 and 315 changed over time.

## Priority 1 — untangle 313 / 315 / 317 and CB's 313 Gallery

Official CBGB history says the record store was replaced in the late 1980s with a second performance/art space, **CB's 313 Gallery**. Secondary real-estate reporting later describes the 313 Gallery as roughly 3,300 sq ft ground floor plus 5,500 sq ft basement next door to the 315 club.

Cornell flyer catalog records from the 1980s also report some CBGB events at `317 Bowery`. Do not normalize these records away.

Research tasks:

- map historic tax lots and address numbering across 313/315/317;
- identify where CBGB Record Canteen, CB's 313 Gallery, cafe/pizza operation, basement performance space and main 315 room connected or remained separate;
- locate architectural/lease floor plans from the 1980s-2000s;
- identify doorway/opening changes between spaces;
- treat every reported address as an observation until the expanded complex is solved.

## Priority 1 — NYC plans, permits and alteration history

Research targets:

- DOB BIS/DOB NOW jobs for BBL 1004570005 / BIN 1006536;
- certificate-of-occupancy/letter-of-no-objection records;
- alteration plans around the 1934 building combination;
- ground-floor plans near the CBGB era;
- 2006-2008 post-club retail alteration plans;
- basement plans and egress diagrams;
- tax maps and PLUTO history;
- LPC/NPS supporting materials;
- Sanborn/fire-insurance sheets for pre-CBGB footprint history.

Administrative `year built` values that conflict with the National Register chronology must be stored as source-specific fields, not used to rewrite history.

## Priority 2 — archival video camera solving

NYU Fales NIGHTCLUBBING footage is potentially our best 1977-1980 spatial evidence because multiple reels repeatedly see the same room from different camera stations.

Highest-value research requests:

- Dead Boys, October 1977 (`305.0001`, `305.0002`);
- Blitz Benefit May 1978, especially edit/backstage/interview/ambience reels (`305.0006`, `305.0007`, `305.0015` and related items);
- the women's-room ambience segment;
- Cuban Heels / Stiletto Fads, April 1979;
- Voidoids, August 1979;
- Destroy All Monsters / Only Ones / Revelons, September 1979;
- Levi and the Rockats, October 1979;
- Bad Brains, December 1979 (`305.0107`);
- Pin-ups / Student Teachers, February 1980.

Research workflow after access/rights review:

1. identify fixed architectural landmarks visible in each reel;
2. annotate camera station and approximate lens/FOV;
3. match repeated features across independent footage;
4. solve camera poses against current/plan-based shell;
5. store observations/timecodes, not unauthorized copied textures;
6. request commercial licenses only for footage we actually need to display or algorithmically derive from beyond permitted research use.

## Priority 2 — historical wide-angle still photography

Target photographers/archives by **spatial value**, not fame alone.

Desired views:

- entrance looking inward;
- stage looking toward entrance;
- side-on bar length;
- room-wide views with ceiling visible;
- stage + adjacent wall/door in one frame;
- backstage/rear transition;
- bathroom/stair path;
- CB's 313 Gallery connection;
- facade showing both 313 and 315 at once;
- side/rear building walls.

High-value rights/outreach targets already identified:

- GODLIS;
- Roberta Bayley;
- Bob Gruen;
- Chris Stein;
- Village Preservation image archive / Meredith Marciano / Carole Teller material;
- NYPL and other institutional collections;
- former employees, bands and tour photographers.

## Priority 2 — Commons/open-image registration

Run `collect_open_assets.py` and then manually review `discovered.json` and `attribution.json`.

For each accepted image:

- verify exact item license again;
- record capture date;
- identify camera orientation/location where possible;
- mark architectural homologous points;
- separate 1975, 2004-2006, 2008 and 2009 states;
- hash the original file;
- never discard attribution/provenance metadata.

Share-alike assets should remain in a clearly tracked derivation branch until license compatibility for the intended output is reviewed.

## Priority 3 — event/history graph expansion

Run `collect_public_metadata.py`, then cross-check discovered events against:

- Cornell flyers;
- MusicBrainz;
- setlist.fm;
- official CBGB history;
- artist archives;
- press/date records;
- NYU footage catalog dates;
- tickets/flyers submitted by collectors.

An event needs stronger corroboration before it drives a public historical scene than it needs to appear as a research lead.

## Priority 3 — artifact measurements

Find surviving physical objects where possible:

- CBGB awning/signage;
- mixing desk/bench;
- bar fixtures;
- stage hardware;
- posters/sign fragments;
- doors/wall panels preserved or displayed after closure.

Museum/collector permissioned photogrammetry can provide exact dimensions and material reference for objects no longer at 315 Bowery.

## Priority 3 — oral-history geometry interviews

Create a structured interview form for former staff, performers, photographers and audience members. Ask spatial questions rather than generic nostalgia:

- draw entrance/bar/stage layout;
- where was the soundboard?;
- how many steps/seconds from door to stage?;
- where were stairs/bathrooms/dressing rooms?;
- what changed between decades?;
- how did CB's 313 Gallery connect?;
- which fixtures were already old when they first visited?;
- where did cameras usually stand?;

Memories receive confidence scores and require corroboration.

## Historical-state evidence buckets

Collect independently:

- pre-1973 Palace Bar/Hilly's state;
- 1973-1976 earliest CBGB / Television / Patti Smith / Ramones period;
- 1977-1982 punk/no-wave peak;
- 1983-1989 hardcore and emergence of 313 Gallery;
- 1990s complex state;
- 2000-2005 late club;
- October 2006 closing state;
- 2008-2009 preserved retail state;
- current surviving fabric.

Never backfill an early state with a late feature unless persistence is evidenced.

## Reference-only hunting list

Search aggressively but store only metadata/links/observations until rights are cleared:

- NYU Fales collections beyond NIGHTCLUBBING, including Lydia Lunch and related Downtown collections;
- Cornell Punk Flyers and manuscript holdings;
- NYPL Digital Collections and manuscript holdings;
- Museum of the City of New York;
- photographer estates/archives;
- documentary film catalogs;
- TV news archives;
- Internet Archive metadata;
- YouTube/Vimeo/social uploads;
- artist/band archives;
- fan/collector scans;
- closing-night material;
- legal/lease records;
- magazines/newspapers;
- books and oral histories.

## Reconstruction confidence rule

Every wall/door/stage/object gets evidence links and separate confidence dimensions.

Suggested bands:

- `0.90-1.00`: measured/current capture or multiple consistent primary sources;
- `0.75-0.89`: strong multi-source historical reconstruction;
- `0.50-0.74`: plausible reconstruction with unresolved measurements;
- `<0.50`: research hypothesis/visual placeholder only.

The public experience must say **Historical Reconstruction** until geometry and rights records justify a stronger accuracy claim.
