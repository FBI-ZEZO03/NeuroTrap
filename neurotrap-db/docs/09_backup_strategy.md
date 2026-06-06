# 09 · Backup Strategy

## 1. Objectives

| Metric | Target |
|--------|--------|
| RPO (max data loss) | ≤ 5 minutes (PITR via oplog) |
| RTO (max downtime to restore) | ≤ 60 minutes (single replica set) |
| Backup retention | daily 30 d · weekly 12 w · monthly 12 m |
| Off-site copies | ≥ 1 region-isolated immutable copy |

## 2. Backup methods (layered)

1. **Continuous PITR** — enable oplog-based point-in-time recovery (Atlas
   Continuous Backups, Ops Manager, or `mongodump --oplog` chained with periodic
   snapshots). Lets us restore to any second within the retention window.
2. **Volume snapshots** — filesystem/EBS snapshots of a hidden secondary on a
   schedule (every 6 h). Fast full-cluster restore; consistent because taken from a
   non-voting hidden node with journaling.
3. **Logical dumps** — nightly `mongndump` of config/reference collections
   (`users`, `roles`, `permissions`, `*_templates`, `deception_profiles`) for
   portable, human-reviewable restores.

## 3. Storage & immutability

- Encrypt backups (KMS) and ship to an object store in a **different region**.
- Enable object-lock / WORM on the off-site bucket to defeat ransomware/tampering.
- Backups inherit the same field-level encryption — credential fields stay
  ciphertext in backups.

## 4. Schedule summary

| Artifact | Cadence | Retention |
|----------|---------|-----------|
| Oplog/PITR | continuous | 7 d window |
| Hidden-secondary snapshot | every 6 h | 30 d |
| Full logical dump | nightly | 30 d |
| Weekly archival snapshot | weekly | 12 w |
| Monthly compliance snapshot | monthly | 12 m (off-site, WORM) |

## 5. Restore drills

- **Monthly** automated restore test: spin a throwaway cluster from the latest
  snapshot + PITR, run `validate_samples.py` and a smoke query suite, record RTO.
- **Quarterly** full game-day: simulate primary loss and a region failover.
- Document every drill (date, artifact, RTO achieved, issues) in the runbook.

## 6. What is *not* backed up the same way

- Cold-archived sessions live in the object store with their own lifecycle/backup;
  not re-dumped from Mongo.
- Regenerable data (`ai_insights`, expired `threat_intel`) is low-priority — covered
  by snapshots but excluded from the nightly logical dump to keep it small.
