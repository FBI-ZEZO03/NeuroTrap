'use strict';
/** deception_profiles — attacker-type → deception-plan strategy (config). */
const mongoose = require('mongoose');
const { Schema } = mongoose;

const DeceptionProfileSchema = new Schema(
  {
    profile_id: { type: String, required: true, unique: true, match: /^dprof_[0-9A-Z]{26}$/ },
    name: { type: String, required: true },
    description: { type: String },
    target_tier: { type: String, required: true, enum: ['beginner', 'automated_bot', 'advanced_human', 'any'] },
    target_intent: { type: String, enum: ['reconnaissance', 'credential_harvesting', 'malware_deployment', 'lateral_movement', 'cryptomining', 'bot_enrollment', 'any'], default: 'any' },
    layers: { type: [String], required: true, enum: ['network', 'host', 'service', 'data', 'credential', 'document', 'token'], validate: v => v.length >= 1 },
    template_refs: { type: [String], default: [] },
    interactivity: { type: String, enum: ['low', 'medium', 'high'], default: 'medium' },
    is_active: { type: Boolean, required: true, default: true }
  },
  { timestamps: { createdAt: 'created_at', updatedAt: 'updated_at' }, collection: 'deception_profiles' }
);

DeceptionProfileSchema.index({ profile_id: 1 }, { unique: true });
DeceptionProfileSchema.index({ target_tier: 1, target_intent: 1, is_active: 1 });

module.exports = mongoose.models.DeceptionProfile || mongoose.model('DeceptionProfile', DeceptionProfileSchema);
