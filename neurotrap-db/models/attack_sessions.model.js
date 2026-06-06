'use strict';
/**
 * attack_sessions — core honeypot telemetry (one doc per session).
 * Highest-write collection: sharded on { source_ip: 'hashed' }, raw TTL/tiering at 90d.
 * Embedded child arrays are bounded & owned; *_ref fields reference shared profiles.
 */
const mongoose = require('mongoose');
const { Schema } = mongoose;

const CommandSchema = new Schema(
  { ts: { type: Date, required: true }, command: { type: String, required: true }, exit_code: { type: Number, default: null } },
  { _id: false }
);
const FileSchema = new Schema(
  { path: { type: String, required: true }, operation: { type: String, required: true, enum: ['read', 'write', 'delete', 'download', 'upload', 'execute'] }, sha256: { type: String, default: null } },
  { _id: false }
);
const CredSchema = new Schema(
  { username: { type: String, required: true }, password: { type: String, default: null }, success: { type: Boolean, default: false } },
  { _id: false }
);
const TimelineSchema = new Schema(
  { ts: { type: Date, required: true }, event_type: { type: String, required: true, enum: ['connect', 'auth', 'command', 'file', 'download', 'disconnect', 'anomaly'] }, detail: { type: String } },
  { _id: false }
);

const AttackSessionSchema = new Schema(
  {
    session_id: { type: String, required: true, unique: true, match: /^sess_[0-9A-Z]{26}$/ },
    source_ip: { type: String, required: true },
    source_port: { type: Number, min: 0, max: 65535 },
    destination_service: { type: String, required: true },
    destination_port: { type: Number, min: 0, max: 65535 },
    protocol: { type: String, required: true, enum: ['ssh', 'telnet', 'http', 'https', 'ftp', 'smb', 'rdp', 'mysql', 'mssql', 'snmp', 'vnc', 'sip', 'other'] },
    honeypot_source: { type: String, required: true, enum: ['cowrie', 'dionaea', 'opencanary', 'galah', 'other'] },
    start_time: { type: Date, required: true },
    end_time: { type: Date, default: null },
    duration_seconds: { type: Number, min: 0, default: null },
    session_status: { type: String, required: true, enum: ['active', 'closed', 'timed_out', 'terminated'], default: 'active' },
    risk_score: { type: Number, min: 0, max: 100, default: 0 },
    threat_actor_ref: { type: String, default: null },
    digital_twin_ref: { type: String, default: null },
    deception_environment_ref: { type: String, default: null },
    commands_executed: { type: [CommandSchema], default: [] },
    files_accessed: { type: [FileSchema], default: [] },
    credentials_attempted: { type: [CredSchema], default: [] },
    session_timeline: { type: [TimelineSchema], default: [] },
    tags: { type: [String], default: [] }
  },
  { timestamps: { createdAt: 'created_at', updatedAt: 'updated_at' }, collection: 'attack_sessions' }
);

AttackSessionSchema.index({ session_id: 1 }, { unique: true });
AttackSessionSchema.index({ source_ip: 1, start_time: -1 });
AttackSessionSchema.index({ session_status: 1, start_time: -1 });
AttackSessionSchema.index({ risk_score: -1 });
AttackSessionSchema.index({ threat_actor_ref: 1 });
AttackSessionSchema.index({ protocol: 1, honeypot_source: 1 });

module.exports = mongoose.models.AttackSession || mongoose.model('AttackSession', AttackSessionSchema);
