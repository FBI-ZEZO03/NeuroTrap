'use strict';
/** deception_effectiveness — engagement metrics + success score per env/session. */
const mongoose = require('mongoose');
const { Schema } = mongoose;

const MetricsSchema = new Schema(
  {
    session_duration: { type: Number, required: true, min: 0 },
    time_spent_in_environment: { type: Number, required: true, min: 0 },
    commands_executed_count: { type: Number, min: 0, default: 0 },
    files_accessed_count: { type: Number, min: 0, default: 0 },
    credentials_attempted_count: { type: Number, min: 0, default: 0 },
    services_explored_count: { type: Number, min: 0, default: 0 },
    lateral_movement_attempts: { type: Number, min: 0, default: 0 }
  },
  { _id: false }
);
const CanaryEvt = new Schema({ token_ref: { type: String, required: true }, ts: { type: Date, required: true } }, { _id: false });
const TrendSchema = new Schema({ ts: { type: Date, required: true }, score: { type: Number, required: true, min: 0, max: 100 } }, { _id: false });

const DeceptionEffectivenessSchema = new Schema(
  {
    effectiveness_id: { type: String, required: true, unique: true, match: /^deff_[0-9A-Z]{26}$/ },
    environment_ref: { type: String, required: true },
    session_ref: { type: String, required: true },
    engagement_metrics: { type: MetricsSchema, required: true },
    canary_trigger_events: { type: [CanaryEvt], default: [] },
    deception_success_score: { type: Number, required: true, min: 0, max: 100 },
    historical_effectiveness_trends: { type: [TrendSchema], default: [] }
  },
  { timestamps: { createdAt: 'created_at', updatedAt: 'updated_at' }, collection: 'deception_effectiveness' }
);

DeceptionEffectivenessSchema.index({ effectiveness_id: 1 }, { unique: true });
DeceptionEffectivenessSchema.index({ environment_ref: 1 });
DeceptionEffectivenessSchema.index({ session_ref: 1 });
DeceptionEffectivenessSchema.index({ deception_success_score: -1 });

module.exports = mongoose.models.DeceptionEffectiveness || mongoose.model('DeceptionEffectiveness', DeceptionEffectivenessSchema);
