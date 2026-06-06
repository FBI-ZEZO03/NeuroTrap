'use strict';
/** analyst_profiles — analyst metadata (specialties, shift, workload), 1:1 with users. */
const mongoose = require('mongoose');
const { Schema } = mongoose;

const WorkloadSchema = new Schema(
  { open_cases: { type: Number, min: 0, default: 0 }, max_cases: { type: Number, min: 1, default: 10 } },
  { _id: false }
);

const AnalystProfileSchema = new Schema(
  {
    user_ref: { type: String, required: true, unique: true, match: /^usr_[0-9A-Z]{26}$/ },
    display_name: { type: String },
    specialties: { type: [String], enum: ['malware', 'network', 'web', 'linux', 'windows', 'threat_intel', 'deception', 'forensics'], default: [] },
    shift: { type: String, enum: ['day', 'swing', 'night', 'on_call'], required: true },
    seniority: { type: String, enum: ['junior', 'mid', 'senior', 'lead'] },
    workload: { type: WorkloadSchema, required: true, default: () => ({ open_cases: 0, max_cases: 10 }) }
  },
  { timestamps: { createdAt: 'created_at', updatedAt: 'updated_at' }, collection: 'analyst_profiles' }
);

AnalystProfileSchema.index({ user_ref: 1 }, { unique: true });
AnalystProfileSchema.index({ shift: 1, 'workload.open_cases': 1 });

module.exports = mongoose.models.AnalystProfile || mongoose.model('AnalystProfile', AnalystProfileSchema);
