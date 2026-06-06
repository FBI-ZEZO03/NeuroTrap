'use strict';
/** reports — generated daily/weekly/incident/executive reports + PDF refs. */
const mongoose = require('mongoose');
const { Schema } = mongoose;

const MetaSchema = new Schema(
  {
    total_sessions: { type: Number, min: 0, default: 0 },
    unique_actors: { type: Number, min: 0, default: 0 },
    critical_alerts: { type: Number, min: 0, default: 0 },
    top_techniques: { type: [String], default: [] },
    deception_success_avg: { type: Number, min: 0, max: 100 }
  },
  { _id: false }
);

const ReportSchema = new Schema(
  {
    report_id: { type: String, required: true, unique: true, match: /^rpt_[0-9A-Z]{26}$/ },
    report_type: { type: String, required: true, enum: ['daily', 'weekly', 'incident', 'executive'] },
    title: { type: String, required: true },
    period_start: { type: Date, required: true },
    period_end: { type: Date, required: true },
    status: { type: String, required: true, enum: ['queued', 'generating', 'ready', 'failed'], default: 'queued' },
    generated_by: { type: String, default: null },
    generated_pdf_ref: { type: String, default: null },
    incident_session_refs: { type: [String], default: [] },
    report_metadata: { type: MetaSchema, default: () => ({}) },
    generated_at: { type: Date, required: true }
  },
  { timestamps: { createdAt: 'created_at', updatedAt: 'updated_at' }, collection: 'reports' }
);

ReportSchema.index({ report_id: 1 }, { unique: true });
ReportSchema.index({ report_type: 1, period_start: -1 });
ReportSchema.index({ status: 1, generated_at: -1 });

module.exports = mongoose.models.Report || mongoose.model('Report', ReportSchema);
