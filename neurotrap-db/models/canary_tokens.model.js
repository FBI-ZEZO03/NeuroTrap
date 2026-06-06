'use strict';
/** canary_tokens — Thinkst-style canarytokens with out-of-band alerting. */
const mongoose = require('mongoose');
const { Schema } = mongoose;

const TriggerSchema = new Schema(
  { ts: { type: Date, required: true }, source_ip: { type: String, required: true }, user_agent: String, alert_ref: { type: String, default: null } },
  { _id: false }
);

const CanaryTokenSchema = new Schema(
  {
    token_id: { type: String, required: true, unique: true, match: /^ctok_[0-9A-Z]{26}$/ },
    environment_ref: { type: String, default: null },
    canary_type: { type: String, required: true, enum: ['dns', 'http_url', 'aws_key', 'doc', 'qr', 'smtp', 'wireguard'] },
    trigger_value: { type: String },
    alert_channel: { type: String, required: true, enum: ['email', 'slack', 'telegram', 'webhook'] },
    active: { type: Boolean, required: true, default: true },
    triggered: { type: Boolean, required: true, default: false },
    trigger_count: { type: Number, min: 0, default: 0 },
    trigger_events: { type: [TriggerSchema], default: [] }
  },
  { timestamps: { createdAt: 'created_at', updatedAt: 'updated_at' }, collection: 'canary_tokens' }
);

CanaryTokenSchema.index({ token_id: 1 }, { unique: true });
CanaryTokenSchema.index({ environment_ref: 1 });
CanaryTokenSchema.index({ triggered: 1, active: 1 });

module.exports = mongoose.models.CanaryToken || mongoose.model('CanaryToken', CanaryTokenSchema);
