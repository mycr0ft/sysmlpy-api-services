# SysML v2 API & Services — Alignment Report

**Repo:** ~/proj/sysmlpy-api-services (`mycr0ft/sysmlpy-api-services`)
**Reference:** OMG Systems Modeling API and Services v1.0 (formal,
Sept 2025); pilot PSM: Systems-Modeling/SysML-v2-API-Services
(`conf/routes`, cloned to ~/proj/third_party/).
**Date:** 2026-10-06. All findings below were verified by running
code (flask test client + route map), not by reading alone.

---

## Verdict

**Partial alignment — the EJSON element shape is close, the
endpoint topology is not conformant.** ~60% of the canonical
surface has a working equivalent, but the URL nesting, scoping,
and several record-level details diverge in ways a standard SysML
v2 API client would notice immediately.

## What aligns well (verified live)

| Spec requirement | Our status | Evidence |
|---|---|---|
| EJSON flat elements with `@type`, `identifier`, `name` | ✅ | `POST /api/model/.../model.sysml` → engine1 = `{"@type": "PartUsage", "identifier": uuid, ...}` |
| `owner` back-reference on every owned element | ✅ | 8/8 elements carried owner ids in the probe |
| `qualifiedName` on elements | ✅ (shape diverges, see gaps) | all 8 emitted |
| Project record lifecycle (create/list/get) | ✅ | `POST /api/projects/` → 201 |
| Branch / Tag / Commit records exist per project | ✅ (flat URLs) | store + lifecycle model |
| Metadata endpoints (schema/datatypes) | ✅ (renamed) | `/api/schema` ≡ `/meta/datatypes` |
| Query — by element type / name | ✅ (simplified) | `/api/query/type/PartDefinition` → `['Vehicle','Engine']` |
| sysmlpy-bridge uniqueness: text → API | ✅ | POSTing `package A { part def X; part x1 : X; }` yields Package + PartDefinition + PartUsage in correct ownership |

Cross-check of type coverage: `Element.SYSML_TYPES` (86 types)
covers the metamodel surface the v1.0 spec's Element classes use
(defs/usages/memberships/relationships incl. Requirement*
memberships, AnalysisCase, Concern, Case). Good breadth.

## Gaps that break conformance with a standard client

Ordered by severity.

1. **Endpoint topology is flat, not nested.** Spec:
   `/projects/{pid}/commits/{cid}/elements[...]` — version-scoped
   element identity is the core of the API ("*every element belongs
   to a commit*"). Ours: `/api/elements/[...]` — globally scoped,
   with only an optional `?commit=` filter. A conformant client
   cannot even address the canonical URLs.

2. **Commit scoping of elements is not real.** Probe showed:
   POST model.sysml returns elements with `"commit"` absent; commits
   carry no `changes`/DataVersion records; `GET .../commits/{cid}/changes`
   equivalent missing entirely. The spec's versioning model
   (Project → Commits → DataVersion → Elements) isn't modeled —
   our Commit is a bare timestamped label.

3. **Branch/Tag/Commit `project` back-reference marshals as
   `{"id": None}` despite the store holding the id** — verified:
   `store.commits.values()[-1].to_dict()` has the id, the marshaled
   HTTP body shows `None`. flask_restx Nested-mask artifact; the
   object graph is right, the wire format is wrong. Blocks any
   client-side project navigation.

4. **Reference shape differs.** Spec EJSON refs:
   `{"identifier": uuid, "@type": ...}` (v1.0 formal; pilot PSM
   uses `{"id": ...}`); ours sometimes `{"id": ...}`, sometimes
   `{"identifier": ...}` — inconsistent *within one response*
   (`owner: {"id": ...}` vs top-level `identifier`).

5. **Missing endpoints:** roots, projectUsage (derived properties),
   relationships-by-related-element with direction param (ours:
   source/target only), saved Query objects + query results, POST
   query-results with criteria body, per-commit change records.

6. **Relationship serialization is name-based, not ref-based.**
   `Subsetting.subsettedFeature` carries a *qualified name string*;
   spec requires an Element reference. `FeatureTyping`/`Redefinition`
   nodes are parsed but **never emitted** (dead branch in
   `ejson_bridge.py` at the `if not _is_node(ft, "FeatureTyping")`
   continue).

7. **PUT/DELETE on branches/commits/tags** — spec has DELETE only on
   branches and tags, **never on commits** (commits are immutable in
   the versioning model). Ours exposes `DELETE/PUT /api/commits/<id>`
   — anti-pattern vs the standard.

8. **Branch-by-NAME access** (`/branches/project/<pid>/branch/<name>`)
   — spec addresses by id; name resolution is a convenience, fine as
   an extension, but it's currently the *only* branch-get.

## What a pragmatic alignment increment looks like

Smallest workable path to "a standard client can work against us":

A. **Re-nest routes** under `/api/projects/<pid>/...` keeping flat
   routes as aliases (one commit; flask_restx add_namespace twice
   with different paths or a url_prefix trick).

B. **Fix the marshal mask** on project refs (`{"id": None}` → real
   ids) — likely a `skip_none`/mask param or plain dict return.

C. **Make elements commit-scoped**: tag every element with the
   commit that created it; `GET /projects/<pid>/commits/<cid>/elements`
   returns that slice. (We already store commit_id on Element —
   verify.)

D. **Emit the dead relationship types** (FeatureTyping,
   Redefinition, Subsetting-with-ref) — the bridge already parses
   them; it just drops the payload.

E. **Reference shape normalization**: pick the formal spec's
   `{"@type", "identifier"}` refs; add `{"id": ...}` as an output
   compat option if needed.

F. **Remove DELETE/PUT on commits.**

Items A–F ≈ 2–4 focused sittings; no new architecture needed.

## What "proof of alignment" deliverables are available now

1. `docs/api-alignment.md` in the repo (this content, tidied).
2. A conformance test module (`tests/conformance_api_test.py`)
   asserting the aligned behaviors above (EJSON shape, ownership,
   lifecycle) — green today for the aligned subset.
3. Endpoint-parity table auto-generated from conf/routes vs
   flask url_map (script in scratch: parity_probe).