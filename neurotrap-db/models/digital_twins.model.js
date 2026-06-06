'use strict';
/** digital_twins — cross-session behavioural replica of an attacker (warm, multi-year). */
const mongoose = require('mongoose');
const { Schema } = mongoose;

const FingerprintSchema = new Schema(
  { hash: { type: String, required: true }, feature_vector: { type: [Number], default: [] }, automation_score: { type: Number, min: 0, max: 100 }, sophistication: { type: Number, min: 0, max: 100 } },
  { _id: false }
);
const SimSchema = new Schema({ digital_twin_ref: { type: String, required: true }, similarity_score: { type: Number, required: true, min: 0, max: 1 } }, { _id: false });
const RiskEvoSchema = new Schema({ ts: { type: Date, required: true }, risk_score: { type: Number, required: true, min: 0, max: 100 } }, { _id: false });
const GeoSchema = new Schema({ country: String, weight: { type: Number, min: 0, max: 1 } }, { _id: false });
const KillChainSchema = new Schema({ current_stage: String, progress: { type: Number, min: 0, max: 1 } }, { _id: false });

const DigitalTwinSchema = new Schema(
  {
    digital_twin_id: { type: String, required: true, unique: true, match: /^dt_[0-9A-Z]{26}$/ },
    attacker_id: { type: String, required: true, match: /^actor_[0-9A-Z]{26}$/ },
    behavioral_fingerprint: { type: FingerprintSchema, required: true },
    confidence_score: { type: Number, required: true, min: 0, max: 1 },
    similarity_scores: { type: [SimSchema], default: [] },
    historical_sessions: { type: [String], default: [] },
    preferred_tools: { type: [String], default: [] },
    preferred_protocols: { type: [String], default: [] },
    preferred_targets: { type: [String], default: [] },
    activity_patterns: { type: Schema.Types.Mixed, default: {} },
    operating_hours: { type: [Number], default: [] },
    geographic_patterns: { type: [GeoSchema], default: [] },
    mitre_techniques_used: { type: [String], default: [] },
    risk_evolution: { type: [RiskEvoSchema], default: [] },
    behavioral_trends: { type: [Schema.Types.Mixed], default: [] },
    session_correlations: { type: [Schema.Types.Mixed], default: [] },
    kill_chain: { type: KillChainSchema, default: () => ({}) },
    first_modeled: { type: Date, required: true },
    last_updated: { type: Date, required: true }
  },
  { timestamps: { createdAt: 'created_at', updatedAt: 'updated_at' }, collection: 'digital_twins' }
);

DigitalTwinSchema.index({ digital_twin_id: 1 }, { unique: true });
DigitalTwinSchema.index({ attacker_id: 1 }, { unique: true });
DigitalTwinSchema.index({ 'behavioral_fingerprint.hash': 1 });
DigitalTwinSchema.index({ mitre_techniques_used: 1 });
DigitalTwinSchema.index({ last_updated: -1 });

module.exports = mongoose.models.DigitalTwin || mongoose.model('DigitalTwin', DigitalTwinSchema);
