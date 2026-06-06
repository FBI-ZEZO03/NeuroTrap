'use strict';
/** ai_insights — predictions, campaign/anomaly/behaviour ML results. */
const mongoose = require('mongoose');
const { Schema } = mongoose;

const ScopeSchema = new Schema({ type: { type: String, required: true, enum: ['session', 'actor', 'twin', 'global'] }, ref: { type: String, default: null } }, { _id: false });
const NextStepSchema = new Schema({ tactic: String, technique_id: String, probability: { type: Number, min: 0, max: 1 } }, { _id: false });
const ThreatPredSchema = new Schema({ label: { type: String, required: true }, probability: { type: Number, required: true, min: 0, max: 1 }, horizon_hours: { type: Number, min: 0 } }, { _id: false });
const CampResSchema = new Schema({ campaign_ref: { type: String, required: true }, score: { type: Number, required: true, min: 0, max: 1 } }, { _id: false });
const AnomResSchema = new Schema({ metric: { type: String, required: true }, anomaly_score: { type: Number, required: true, min: 0, max: 1 }, is_anomaly: { type: Boolean, default: false } }, { _id: false });
const BehavPredSchema = new Schema({ metric: { type: String, required: true }, predicted_value: { type: Number, required: true } }, { _id: false });

const AiInsightSchema = new Schema(
  {
    insight_id: { type: String, required: true, unique: true, match: /^ains_[0-9A-Z]{26}$/ },
    scope: { type: ScopeSchema, required: true },
    predicted_next_attack_step: { type: NextStepSchema, default: undefined },
    threat_predictions: { type: [ThreatPredSchema], default: [] },
    campaign_detection_results: { type: [CampResSchema], default: [] },
    anomaly_detection_results: { type: [AnomResSchema], default: [] },
    behavioral_predictions: { type: [BehavPredSchema], default: [] },
    ai_confidence_score: { type: Number, required: true, min: 0, max: 1 },
    generated_at: { type: Date, required: true }
  },
  { timestamps: { createdAt: 'created_at', updatedAt: 'updated_at' }, collection: 'ai_insights' }
);

AiInsightSchema.index({ insight_id: 1 }, { unique: true });
AiInsightSchema.index({ 'scope.type': 1, 'scope.ref': 1, generated_at: -1 });

module.exports = mongoose.models.AiInsight || mongoose.model('AiInsight', AiInsightSchema);
