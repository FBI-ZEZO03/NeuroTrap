'use strict';
/** threat_intel — enrichment cache keyed by indicator (VT/AbuseIPDB/Shodan/OTX/GeoIP). */
const mongoose = require('mongoose');
const { Schema } = mongoose;

// strict:false on provider sub-objects — third-party payloads evolve.
const Open = (extra = {}) => new Schema(extra, { _id: false, strict: false });

const ThreatIntelSchema = new Schema(
  {
    indicator: { type: String, required: true, unique: true },
    indicator_type: { type: String, required: true, enum: ['ipv4', 'ipv6', 'domain', 'url', 'sha256', 'md5'] },
    reputation_score: { type: Number, required: true, min: 0, max: 100 },
    virustotal: { type: Open(), default: undefined },
    abuseipdb: { type: Open(), default: undefined },
    shodan: { type: Open(), default: undefined },
    otx: { type: Open(), default: undefined },
    geoip: { type: Open(), default: undefined },
    threat_feeds: { type: [Open()], default: [] },
    enrichment_history: { type: [Open()], default: [] },
    fetched_at: { type: Date, required: true },
    expires_at: { type: Date, required: true }
  },
  { timestamps: { createdAt: 'created_at', updatedAt: 'updated_at' }, collection: 'threat_intel' }
);

ThreatIntelSchema.index({ indicator: 1 }, { unique: true });
ThreatIntelSchema.index({ reputation_score: -1 });
// TTL: drop cache entries at expiry so the enrichment worker re-fetches.
ThreatIntelSchema.index({ expires_at: 1 }, { expireAfterSeconds: 0 });

module.exports = mongoose.models.ThreatIntel || mongoose.model('ThreatIntel', ThreatIntelSchema);
