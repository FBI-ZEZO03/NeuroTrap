'use strict';
/** honey_tokens — in-environment honey tokens + trigger tracking. */
const mongoose = require('mongoose');
const { Schema } = mongoose;

const TriggerSchema = new Schema(
  { ts: { type: Date, required: true }, source_ip: { type: String, required: true }, session_ref: { type: String, default: null } },
  { _id: false }
);

const HoneyTokenSchema = new Schema(
  {
    token_id: { type: String, required: true, unique: true, match: /^htok_[0-9A-Z]{26}$/ },
    environment_ref: { type: String, required: true },
    token_type: { type: String, required: true, enum: ['api_key', 'url_beacon', 'db_row', 'registry_key', 'env_var', 'qr'] },
    token_value: { type: String, required: true },
    planted_location: { type: String },
    triggered: { type: Boolean, required: true, default: false },
    trigger_count: { type: Number, min: 0, default: 0 },
    trigger_events: { type: [TriggerSchema], default: [] }
  },
  { timestamps: { createdAt: 'created_at', updatedAt: 'updated_at' }, collection: 'honey_tokens' }
);

HoneyTokenSchema.index({ token_id: 1 }, { unique: true });
HoneyTokenSchema.index({ environment_ref: 1 });
HoneyTokenSchema.index({ triggered: 1 });

module.exports = mongoose.models.HoneyToken || mongoose.model('HoneyToken', HoneyTokenSchema);
