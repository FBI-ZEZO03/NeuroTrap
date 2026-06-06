'use strict';
/** response_actions — autonomous response decisions + audit history. */
const mongoose = require('mongoose');
const { Schema } = mongoose;

const STATUS = ['pending', 'applied', 'failed', 'reverted', 'expired'];
const DecisionLog = new Schema({ ts: { type: Date, required: true }, message: { type: String, required: true }, rule: String }, { _id: false });
const HistoryLog = new Schema({ ts: { type: Date, required: true }, status: { type: String, required: true, enum: STATUS }, note: String }, { _id: false });

const ResponseActionSchema = new Schema(
  {
    action_id: { type: String, required: true, unique: true, match: /^act_[0-9A-Z]{26}$/ },
    related_session: { type: String, required: true },
    related_actor: { type: String, default: null },
    threat_score: { type: Number, required: true, min: 0, max: 100 },
    risk_level: { type: String, required: true, enum: ['low', 'medium', 'high', 'critical'] },
    action_type: { type: String, required: true, enum: ['block', 'redirect', 'isolate', 'tarpit', 'monitor'] },
    automated_decision: { type: Boolean, required: true, default: true },
    decided_by: { type: String, default: null },
    target_ip: { type: String },
    status: { type: String, required: true, enum: STATUS, default: 'pending' },
    applied_at: { type: Date, default: null },
    expires_at: { type: Date, default: null },
    decision_logs: { type: [DecisionLog], default: [] },
    response_history: { type: [HistoryLog], default: [] }
  },
  { timestamps: { createdAt: 'created_at', updatedAt: 'updated_at' }, collection: 'response_actions' }
);

ResponseActionSchema.index({ action_id: 1 }, { unique: true });
ResponseActionSchema.index({ related_session: 1 });
ResponseActionSchema.index({ target_ip: 1, status: 1 });
ResponseActionSchema.index({ status: 1, created_at: -1 });

module.exports = mongoose.models.ResponseAction || mongoose.model('ResponseAction', ResponseActionSchema);
