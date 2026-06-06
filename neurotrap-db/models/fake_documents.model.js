'use strict';
/** fake_documents — decoy documents/assets (may embed a canary/honey token). */
const mongoose = require('mongoose');
const { Schema } = mongoose;

const FakeDocumentSchema = new Schema(
  {
    document_id: { type: String, required: true, unique: true, match: /^fdoc_[0-9A-Z]{26}$/ },
    environment_ref: { type: String, required: true },
    filename: { type: String, required: true },
    doc_type: { type: String, required: true, enum: ['pdf', 'docx', 'xlsx', 'txt', 'env_file', 'config', 'source_code', 'email'] },
    title: { type: String },
    sensitivity_label: { type: String, enum: ['public', 'internal', 'confidential', 'secret'], default: 'internal' },
    content_ref: { type: String, default: null },
    embedded_token_ref: { type: String, default: null }
  },
  { timestamps: { createdAt: 'created_at', updatedAt: 'updated_at' }, collection: 'fake_documents' }
);

FakeDocumentSchema.index({ document_id: 1 }, { unique: true });
FakeDocumentSchema.index({ environment_ref: 1 });

module.exports = mongoose.models.FakeDocument || mongoose.model('FakeDocument', FakeDocumentSchema);
