'use strict';
/** login_history — authentication audit events (TTL 365d, see 08_retention). */
const mongoose = require('mongoose');
const { Schema } = mongoose;

const GeoSchema = new Schema(
  { country: String, city: String, lat: { type: Number, min: -90, max: 90 }, lon: { type: Number, min: -180, max: 180 } },
  { _id: false }
);

const LoginHistorySchema = new Schema(
  {
    user_ref: { type: String, required: true, match: /^usr_[0-9A-Z]{26}$/ },
    username_attempted: { type: String },
    ip: { type: String, required: true },
    user_agent: { type: String },
    success: { type: Boolean, required: true },
    failure_reason: { type: String, enum: ['bad_password', 'no_such_user', 'locked', 'mfa_failed', 'expired', null], default: null },
    mfa_used: { type: Boolean, default: false },
    geo: { type: GeoSchema, default: undefined }
  },
  { timestamps: { createdAt: 'created_at', updatedAt: 'updated_at' }, collection: 'login_history' }
);

LoginHistorySchema.index({ user_ref: 1, created_at: -1 });
LoginHistorySchema.index({ ip: 1, created_at: -1 });
// TTL: expire 365 days after creation (compliance window).
LoginHistorySchema.index({ created_at: 1 }, { expireAfterSeconds: 31536000 });

module.exports = mongoose.models.LoginHistory || mongoose.model('LoginHistory', LoginHistorySchema);
