'use strict';
/** permissions — granular resource:action permission catalog. */
const mongoose = require('mongoose');
const { Schema } = mongoose;

const PermissionSchema = new Schema(
  {
    permission_id: { type: String, required: true, unique: true, match: /^perm_[a-z0-9_]+:[a-z]+$/ },
    resource: {
      type: String, required: true,
      enum: ['users', 'roles', 'permissions', 'sessions', 'actors', 'intel', 'mitre', 'response', 'alerts', 'reports', 'deception', 'ai', 'twins', 'campaigns']
    },
    action: { type: String, required: true, enum: ['read', 'write', 'delete', 'execute', 'review'] },
    description: { type: String, required: true, maxlength: 256 }
  },
  { timestamps: { createdAt: 'created_at', updatedAt: 'updated_at' }, collection: 'permissions' }
);

PermissionSchema.index({ permission_id: 1 }, { unique: true });
PermissionSchema.index({ resource: 1, action: 1 });

module.exports = mongoose.models.Permission || mongoose.model('Permission', PermissionSchema);
