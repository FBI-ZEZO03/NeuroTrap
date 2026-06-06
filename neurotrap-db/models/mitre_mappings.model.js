'use strict';
/** mitre_mappings — technique observed per session with evidence (high write). */
const mongoose = require('mongoose');
const { Schema } = mongoose;

const EvidenceSchema = new Schema(
  { type: { type: String, required: true, enum: ['command', 'file', 'network', 'auth', 'signature'] }, value: { type: String, required: true }, ts: { type: Date, default: null } },
  { _id: false }
);

const TACTICS = ['reconnaissance', 'resource_development', 'initial_access', 'execution', 'persistence', 'privilege_escalation', 'defense_evasion', 'credential_access', 'discovery', 'lateral_movement', 'collection', 'command_and_control', 'exfiltration', 'impact'];

const MitreMappingSchema = new Schema(
  {
    mapping_id: { type: String, required: true, unique: true, match: /^map_[0-9A-Z]{26}$/ },
    technique_id: { type: String, required: true, match: /^T[0-9]{4}(\.[0-9]{3})?$/ },
    technique_name: { type: String, required: true },
    tactic: { type: String, required: true, enum: TACTICS },
    description: { type: String },
    confidence_score: { type: Number, required: true, min: 0, max: 1 },
    related_session: { type: String, required: true },
    related_actor: { type: String, default: null },
    detection_evidence: { type: [EvidenceSchema], default: [] }
  },
  { timestamps: { createdAt: 'created_at', updatedAt: 'updated_at' }, collection: 'mitre_mappings' }
);

MitreMappingSchema.index({ mapping_id: 1 }, { unique: true });
MitreMappingSchema.index({ technique_id: 1 });
MitreMappingSchema.index({ related_session: 1 });
MitreMappingSchema.index({ tactic: 1, technique_id: 1 });

module.exports = mongoose.models.MitreMapping || mongoose.model('MitreMapping', MitreMappingSchema);
