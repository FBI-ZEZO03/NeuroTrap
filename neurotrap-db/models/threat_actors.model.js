'use strict';
/** threat_actors — persistent per-source attacker profile (warm, multi-year). */
const mongoose = require('mongoose');
const { Schema } = mongoose;

const HistorySchema = new Schema(
  { session_ref: { type: String, required: true }, ts: { type: Date, required: true }, risk_score: { type: Number, min: 0, max: 100, required: true }, summary: String },
  { _id: false }
);
const ProfileSchema = new Schema(
  {
    tier: { type: String, enum: ['beginner', 'automated_bot', 'advanced_human'] },
    primary_intent: { type: String, enum: ['reconnaissance', 'credential_harvesting', 'malware_deployment', 'lateral_movement', 'cryptomining', 'bot_enrollment', 'unknown'] },
    preferred_protocols: { type: [String], default: [] }
  },
  { _id: false }
);

const ThreatActorSchema = new Schema(
  {
    actor_id: { type: String, required: true, unique: true, match: /^actor_[0-9A-Z]{26}$/ },
    primary_ip: { type: String, required: true },
    known_ips: { type: [String], default: [] },
    attacker_profile: { type: ProfileSchema, default: () => ({}) },
    classification: { type: String, required: true, enum: ['scanner', 'bruteforcer', 'botnet', 'apt', 'researcher', 'unknown'] },
    risk_score: { type: Number, required: true, min: 0, max: 100 },
    reputation_score: { type: Number, required: true, min: 0, max: 100 },
    country: { type: String, default: null },
    asn: { type: Number, default: null },
    isp: { type: String, default: null },
    session_count: { type: Number, min: 0, default: 0 },
    threat_history: { type: [HistorySchema], default: [] },
    historical_session_refs: { type: [String], default: [] },
    digital_twin_ref: { type: String, default: null },
    first_seen: { type: Date, required: true },
    last_seen: { type: Date, required: true }
  },
  { timestamps: { createdAt: 'created_at', updatedAt: 'updated_at' }, collection: 'threat_actors' }
);

ThreatActorSchema.index({ actor_id: 1 }, { unique: true });
ThreatActorSchema.index({ primary_ip: 1 });
ThreatActorSchema.index({ known_ips: 1 });
ThreatActorSchema.index({ risk_score: -1 });
ThreatActorSchema.index({ classification: 1, last_seen: -1 });

module.exports = mongoose.models.ThreatActor || mongoose.model('ThreatActor', ThreatActorSchema);
