'use strict';
/** generated_environments — concrete environment instances (template → active → retired). */
const mongoose = require('mongoose');
const { Schema } = mongoose;

const GeneratedEnvironmentSchema = new Schema(
  {
    environment_id: { type: String, required: true, unique: true, match: /^env_[0-9A-Z]{26}$/ },
    template_ref: { type: String, required: true },
    profile_ref: { type: String, required: true },
    target_actor_ref: { type: String, default: null },
    target_session_ref: { type: String, default: null },
    status: { type: String, required: true, enum: ['generated', 'active', 'retired'], default: 'generated' },
    server_refs: { type: [String], default: [] },
    database_refs: { type: [String], default: [] },
    filesystem_refs: { type: [String], default: [] },
    credential_refs: { type: [String], default: [] },
    document_refs: { type: [String], default: [] },
    token_refs: { type: [String], default: [] },
    generated_at: { type: Date, required: true },
    retired_at: { type: Date, default: null }
  },
  { timestamps: { createdAt: 'created_at', updatedAt: 'updated_at' }, collection: 'generated_environments' }
);

GeneratedEnvironmentSchema.index({ environment_id: 1 }, { unique: true });
GeneratedEnvironmentSchema.index({ status: 1, generated_at: -1 });
GeneratedEnvironmentSchema.index({ target_actor_ref: 1 });

module.exports = mongoose.models.GeneratedEnvironment || mongoose.model('GeneratedEnvironment', GeneratedEnvironmentSchema);
