'use strict';
/** roles — RBAC role definitions (admin/analyst/viewer/…). */
const mongoose = require('mongoose');
const { Schema } = mongoose;

const RoleSchema = new Schema(
  {
    role_id: { type: String, required: true, unique: true, match: /^role_[a-z_]+$/ },
    name: { type: String, required: true, minlength: 2, maxlength: 64 },
    description: { type: String, maxlength: 512 },
    permission_refs: { type: [String], default: [] },
    is_system: { type: Boolean, required: true, default: false }
  },
  { timestamps: { createdAt: 'created_at', updatedAt: 'updated_at' }, collection: 'roles' }
);

RoleSchema.index({ role_id: 1 }, { unique: true });

module.exports = mongoose.models.Role || mongoose.model('Role', RoleSchema);
