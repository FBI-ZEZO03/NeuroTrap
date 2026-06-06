'use strict';
/** environment_templates — reusable deception environment blueprints. */
const mongoose = require('mongoose');
const { Schema } = mongoose;

const SpecSchema = new Schema(
  {
    os_banner: String,
    services: { type: [String], enum: ['ssh', 'http', 'https', 'ftp', 'smb', 'mysql', 'mssql', 'rdp'], default: [] },
    server_count: { type: Number, min: 1, default: 1 },
    seed_documents: { type: Number, min: 0, default: 0 },
    seed_credentials: { type: Number, min: 0, default: 0 },
    token_count: { type: Number, min: 0, default: 0 }
  },
  { _id: false }
);

const EnvironmentTemplateSchema = new Schema(
  {
    template_id: { type: String, required: true, unique: true, match: /^tmpl_[0-9A-Z]{26}$/ },
    name: { type: String, required: true },
    industry: { type: String, required: true, enum: ['financial_services', 'saas_startup', 'government', 'e_commerce', 'healthcare', 'generic'] },
    description: { type: String },
    spec: { type: SpecSchema, required: true },
    version: { type: Number, required: true, min: 1, default: 1 },
    is_active: { type: Boolean, required: true, default: true }
  },
  { timestamps: { createdAt: 'created_at', updatedAt: 'updated_at' }, collection: 'environment_templates' }
);

EnvironmentTemplateSchema.index({ template_id: 1 }, { unique: true });
EnvironmentTemplateSchema.index({ industry: 1, is_active: 1 });

module.exports = mongoose.models.EnvironmentTemplate || mongoose.model('EnvironmentTemplate', EnvironmentTemplateSchema);
