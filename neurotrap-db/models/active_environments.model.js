'use strict';
/** active_environments — live deception instances (hot; TTL teardown of retired rows). */
const mongoose = require('mongoose');
const { Schema } = mongoose;

const ActiveEnvironmentSchema = new Schema(
  {
    environment_id: { type: String, required: true, unique: true, match: /^env_[0-9A-Z]{26}$/ },
    generated_environment_ref: { type: String, required: true },
    session_ref: { type: String, required: true },
    actor_ref: { type: String, default: null },
    status: { type: String, required: true, enum: ['active', 'idle', 'retiring', 'retired'], default: 'active' },
    container_id: { type: String, default: null },
    endpoint: { type: String, default: null },
    engagement_seconds: { type: Number, min: 0, default: 0 },
    started_at: { type: Date, required: true },
    last_activity_at: { type: Date, default: null },
    expires_at: { type: Date, required: true }
  },
  { timestamps: { createdAt: 'created_at', updatedAt: 'updated_at' }, collection: 'active_environments' }
);

ActiveEnvironmentSchema.index({ environment_id: 1 }, { unique: true });
ActiveEnvironmentSchema.index({ status: 1, started_at: -1 });
ActiveEnvironmentSchema.index({ session_ref: 1 });
// TTL: remove retired/expired environment records once expires_at passes.
ActiveEnvironmentSchema.index({ expires_at: 1 }, { expireAfterSeconds: 0 });

module.exports = mongoose.models.ActiveEnvironment || mongoose.model('ActiveEnvironment', ActiveEnvironmentSchema);
