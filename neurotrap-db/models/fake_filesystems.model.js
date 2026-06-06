'use strict';
/** fake_filesystems — decoy filesystem trees seeded into fake servers. */
const mongoose = require('mongoose');
const { Schema } = mongoose;

const EntrySchema = new Schema(
  { path: { type: String, required: true }, type: { type: String, required: true, enum: ['file', 'dir', 'symlink'] }, size_bytes: { type: Number, min: 0 }, is_bait: { type: Boolean, default: false } },
  { _id: false }
);

const FakeFilesystemSchema = new Schema(
  {
    filesystem_id: { type: String, required: true, unique: true, match: /^ffs_[0-9A-Z]{26}$/ },
    environment_ref: { type: String, required: true },
    server_ref: { type: String, default: null },
    root_path: { type: String, required: true },
    entries: { type: [EntrySchema], required: true, validate: v => v.length >= 1 }
  },
  { timestamps: { createdAt: 'created_at', updatedAt: 'updated_at' }, collection: 'fake_filesystems' }
);

FakeFilesystemSchema.index({ filesystem_id: 1 }, { unique: true });
FakeFilesystemSchema.index({ environment_ref: 1 });

module.exports = mongoose.models.FakeFilesystem || mongoose.model('FakeFilesystem', FakeFilesystemSchema);
