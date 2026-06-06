'use strict';
/**
 * users — SOC user accounts (RBAC subjects).
 * password_hash / mfa_secret must be encrypted at rest (CSFLE). See 06_security.
 */
const mongoose = require('mongoose');
const { Schema } = mongoose;

const UserSchema = new Schema(
  {
    user_id: { type: String, required: true, unique: true, match: /^usr_[0-9A-Z]{26}$/ },
    username: { type: String, required: true, minlength: 3, maxlength: 64, unique: true },
    email: { type: String, required: true, unique: true, match: /^[^@\s]+@[^@\s]+\.[^@\s]+$/ },
    password_hash: { type: String, required: true },
    status: { type: String, required: true, enum: ['active', 'disabled', 'locked', 'pending'], default: 'pending' },
    mfa_enabled: { type: Boolean, required: true, default: false },
    mfa_secret: { type: String, default: null },
    role_refs: { type: [String], required: true, validate: v => Array.isArray(v) && v.length >= 1 },
    analyst_profile_ref: { type: String, default: null },
    last_login_at: { type: Date, default: null },
    failed_login_count: { type: Number, default: 0, min: 0 }
  },
  { timestamps: { createdAt: 'created_at', updatedAt: 'updated_at' }, collection: 'users' }
);

UserSchema.index({ user_id: 1 }, { unique: true });
UserSchema.index({ email: 1 }, { unique: true });
UserSchema.index({ status: 1 });

module.exports = mongoose.models.User || mongoose.model('User', UserSchema);
