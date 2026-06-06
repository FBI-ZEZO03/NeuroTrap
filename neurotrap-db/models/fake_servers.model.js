'use strict';
/** fake_servers — decoy servers inside a generated environment. */
const mongoose = require('mongoose');
const { Schema } = mongoose;

const ServiceSchema = new Schema(
  { protocol: { type: String, required: true, enum: ['ssh', 'http', 'https', 'ftp', 'smb', 'mysql', 'mssql', 'rdp'] }, port: { type: Number, required: true, min: 1, max: 65535 }, banner: String },
  { _id: false }
);

const FakeServerSchema = new Schema(
  {
    server_id: { type: String, required: true, unique: true, match: /^fsrv_[0-9A-Z]{26}$/ },
    environment_ref: { type: String, required: true },
    hostname: { type: String, required: true },
    ip: { type: String },
    os_banner: { type: String, required: true },
    role: { type: String, enum: ['jump_host', 'web', 'db', 'file', 'domain_controller', 'workstation', 'generic'], default: 'generic' },
    services: { type: [ServiceSchema], required: true, validate: v => v.length >= 1 }
  },
  { timestamps: { createdAt: 'created_at', updatedAt: 'updated_at' }, collection: 'fake_servers' }
);

FakeServerSchema.index({ server_id: 1 }, { unique: true });
FakeServerSchema.index({ environment_ref: 1 });

module.exports = mongoose.models.FakeServer || mongoose.model('FakeServer', FakeServerSchema);
