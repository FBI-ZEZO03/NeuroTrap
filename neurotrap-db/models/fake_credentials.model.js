'use strict';
/** fake_credentials — planted decoy creds (secret_enc field-encrypted; burn-on-use). */
const mongoose = require('mongoose');
const { Schema } = mongoose;

const UseEventSchema = new Schema(
  { ts: { type: Date, required: true }, session_ref: { type: String, required: true }, source_ip: String },
  { _id: false }
);

const FakeCredentialSchema = new Schema(
  {
    credential_id: { type: String, required: true, unique: true, match: /^fcred_[0-9A-Z]{26}$/ },
    environment_ref: { type: String, required: true },
    username: { type: String, required: true },
    secret_enc: { type: String, required: true },
    credential_type: { type: String, required: true, enum: ['password', 'ssh_key', 'api_key', 'aws_key', 'db_password', 'jwt'] },
    planted_location: { type: String },
    use_detected: { type: Boolean, required: true, default: false },
    use_events: { type: [UseEventSchema], default: [] }
  },
  { timestamps: { createdAt: 'created_at', updatedAt: 'updated_at' }, collection: 'fake_credentials' }
);

FakeCredentialSchema.index({ credential_id: 1 }, { unique: true });
FakeCredentialSchema.index({ environment_ref: 1 });
FakeCredentialSchema.index({ use_detected: 1 });

module.exports = mongoose.models.FakeCredential || mongoose.model('FakeCredential', FakeCredentialSchema);
