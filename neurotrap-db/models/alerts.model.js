'use strict';
/** alerts — operational alerts with delivery tracking (hot, 180d then cold). */
const mongoose = require('mongoose');
const { Schema } = mongoose;

const DeliverySchema = new Schema(
  { channel: { type: String, required: true, enum: ['email', 'slack', 'telegram', 'webhook'] }, status: { type: String, required: true, enum: ['pending', 'sent', 'failed'] }, ts: { type: Date, default: null }, error: { type: String, default: null } },
  { _id: false }
);

const AlertSchema = new Schema(
  {
    alert_id: { type: String, required: true, unique: true, match: /^alrt_[0-9A-Z]{26}$/ },
    alert_type: { type: String, required: true, enum: ['new_session', 'high_risk_session', 'credential_use', 'malware_download', 'canary_triggered', 'campaign_detected', 'response_applied', 'system'] },
    severity: { type: String, required: true, enum: ['info', 'low', 'medium', 'high', 'critical'] },
    source: { type: String, required: true, enum: ['detection', 'response_engine', 'deception', 'ai_analyst', 'campaign_engine', 'system'] },
    title: { type: String },
    message: { type: String },
    related_session: { type: String, default: null },
    related_actor: { type: String, default: null },
    assigned_to: { type: String, default: null },
    status: { type: String, required: true, enum: ['open', 'acknowledged', 'resolved', 'suppressed'], default: 'open' },
    notification_status: { type: String, enum: ['pending', 'sent', 'partial', 'failed'], default: 'pending' },
    delivery_tracking: { type: [DeliverySchema], default: [] }
  },
  { timestamps: { createdAt: 'created_at', updatedAt: 'updated_at' }, collection: 'alerts' }
);

AlertSchema.index({ alert_id: 1 }, { unique: true });
AlertSchema.index({ severity: 1, status: 1, created_at: -1 });
AlertSchema.index({ related_session: 1 });
AlertSchema.index({ status: 1, created_at: -1 });

module.exports = mongoose.models.Alert || mongoose.model('Alert', AlertSchema);
