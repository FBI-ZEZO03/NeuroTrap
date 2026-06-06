'use strict';
/** ai_analyst_outputs — AI SOC Analyst explanations + analyst review workflow. */
const mongoose = require('mongoose');
const { Schema } = mongoose;

const RecoSchema = new Schema(
  { action: { type: String, required: true, enum: ['block', 'redirect', 'isolate', 'tarpit', 'monitor'] }, rationale: { type: String, required: true }, priority: { type: String, enum: ['low', 'medium', 'high'], default: 'medium' } },
  { _id: false }
);
const NoteSchema = new Schema({ ts: { type: Date, required: true }, author_ref: { type: String, required: true }, note: { type: String, required: true } }, { _id: false });
const FeedbackSchema = new Schema({ ts: { type: Date, required: true }, rating: { type: String, required: true, enum: ['up', 'down'] }, comment: String }, { _id: false });

const AiAnalystOutputSchema = new Schema(
  {
    output_id: { type: String, required: true, unique: true, match: /^aout_[0-9A-Z]{26}$/ },
    related_session: { type: String, required: true },
    related_actor: { type: String, default: null },
    model: { type: String },
    attack_explanation: { type: String },
    session_summary: { type: String },
    mitre_explanation: { type: String },
    risk_explanation: { type: String },
    explain_why: { type: String },
    recommended_responses: { type: [RecoSchema], default: [] },
    generated_insights: { type: String },
    executive_summary: { type: String },
    incident_report_ref: { type: String, default: null },
    ai_confidence_score: { type: Number, required: true, min: 0, max: 1 },
    review_status: { type: String, required: true, enum: ['generated', 'reviewed', 'approved', 'rejected'], default: 'generated' },
    reviewed_by: { type: String, default: null },
    analyst_notes: { type: [NoteSchema], default: [] },
    analyst_feedback: { type: [FeedbackSchema], default: [] },
    generated_at: { type: Date, required: true }
  },
  { timestamps: { createdAt: 'created_at', updatedAt: 'updated_at' }, collection: 'ai_analyst_outputs' }
);

AiAnalystOutputSchema.index({ output_id: 1 }, { unique: true });
AiAnalystOutputSchema.index({ related_session: 1, generated_at: -1 });
AiAnalystOutputSchema.index({ review_status: 1 });

module.exports = mongoose.models.AiAnalystOutput || mongoose.model('AiAnalystOutput', AiAnalystOutputSchema);
