'use strict';
/** attack_campaigns — correlated multi-actor/multi-session campaigns. */
const mongoose = require('mongoose');
const { Schema } = mongoose;

const InfraSchema = new Schema(
  { type: { type: String, required: true, enum: ['ip', 'asn', 'domain', 'payload_hash', 'ssh_key', 'user_agent'] }, value: { type: String, required: true } },
  { _id: false }
);

const AttackCampaignSchema = new Schema(
  {
    campaign_id: { type: String, required: true, unique: true, match: /^camp_[0-9A-Z]{26}$/ },
    campaign_name: { type: String, required: true },
    description: { type: String },
    status: { type: String, required: true, enum: ['candidate', 'confirmed', 'monitoring', 'closed'], default: 'candidate' },
    related_attackers: { type: [String], default: [] },
    related_sessions: { type: [String], default: [] },
    shared_behaviors: { type: [String], default: [] },
    shared_mitre_techniques: { type: [String], default: [] },
    shared_infrastructure: { type: [InfraSchema], default: [] },
    campaign_confidence_score: { type: Number, required: true, min: 0, max: 1 },
    first_seen: { type: Date, required: true },
    last_seen: { type: Date, required: true }
  },
  { timestamps: { createdAt: 'created_at', updatedAt: 'updated_at' }, collection: 'attack_campaigns' }
);

AttackCampaignSchema.index({ campaign_id: 1 }, { unique: true });
AttackCampaignSchema.index({ status: 1, last_seen: -1 });
AttackCampaignSchema.index({ related_attackers: 1 });
AttackCampaignSchema.index({ shared_mitre_techniques: 1 });

module.exports = mongoose.models.AttackCampaign || mongoose.model('AttackCampaign', AttackCampaignSchema);
