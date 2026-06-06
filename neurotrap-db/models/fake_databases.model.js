'use strict';
/** fake_databases — decoy databases with fabricated tables. */
const mongoose = require('mongoose');
const { Schema } = mongoose;

const TableSchema = new Schema(
  { name: { type: String, required: true }, row_count: { type: Number, required: true, min: 0 }, columns: { type: [String], default: [] }, contains_pii: { type: Boolean, default: false } },
  { _id: false }
);

const FakeDatabaseSchema = new Schema(
  {
    database_id: { type: String, required: true, unique: true, match: /^fdb_[0-9A-Z]{26}$/ },
    environment_ref: { type: String, required: true },
    server_ref: { type: String, default: null },
    engine: { type: String, required: true, enum: ['mysql', 'postgresql', 'mssql', 'mongodb'] },
    db_name: { type: String, required: true },
    tables: { type: [TableSchema], required: true, validate: v => v.length >= 1 }
  },
  { timestamps: { createdAt: 'created_at', updatedAt: 'updated_at' }, collection: 'fake_databases' }
);

FakeDatabaseSchema.index({ database_id: 1 }, { unique: true });
FakeDatabaseSchema.index({ environment_ref: 1 });

module.exports = mongoose.models.FakeDatabase || mongoose.model('FakeDatabase', FakeDatabaseSchema);
