import React, { useState, useEffect, useCallback, useRef } from 'react';
import './ViolationsDashboard.css';

const BACKEND_URL = 'http://localhost:8000';

/**
 * ViolationsDashboard Component
 *
 * Displays all permanently stored overspeed violation records.
 * - Fetches from GET /api/violations on mount
 * - Receives live updates via the shared `latestMessage` prop (from WS)
 * - Supports search by Vehicle ID, sort, refresh, delete, and snapshot lightbox
 *
 * @param {Object|null} latestMessage - Latest WebSocket message from the parent App
 * @param {Function} onClearViolations - Callback to reset top badge count
 * @param {Function} onViolationDeleted - Callback to decrement top badge count
 */
const ViolationsDashboard = ({ latestMessage, onClearViolations, onViolationDeleted }) => {
    const [violations, setViolations] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchId, setSearchId] = useState('');
    const [sortOrder, setSortOrder] = useState('newest');
    const [lightboxSrc, setLightboxSrc] = useState(null);
    const [newRowIds, setNewRowIds] = useState(new Set());
    const prevMessageRef = useRef(null);

    // ── Fetch all violations from REST API ───────────────────────────────────
    const fetchViolations = useCallback(async () => {
        setLoading(true);
        try {
            const res = await fetch(`${BACKEND_URL}/api/violations`);
            if (res.ok) {
                const data = await res.json();
                setViolations(data);
            }
        } catch (err) {
            console.error('Failed to fetch violations:', err);
        } finally {
            setLoading(false);
        }
    }, []);

    // Initial load
    useEffect(() => {
        fetchViolations();
    }, [fetchViolations]);

    // ── Real-time update from WebSocket ──────────────────────────────────────
    useEffect(() => {
        if (!latestMessage || latestMessage === prevMessageRef.current) return;
        prevMessageRef.current = latestMessage;

        if (latestMessage.violation_saved && latestMessage.new_violation) {
            const record = latestMessage.new_violation;
            setViolations(prev => {
                const existingIndex = prev.findIndex(v => v.id === record.id);
                if (existingIndex >= 0) {
                    // Update existing record with new higher speed/timestamp
                    const updatedList = [...prev];
                    updatedList[existingIndex] = record;
                    return updatedList;
                } else {
                    // Insert new record at the top
                    return [record, ...prev];
                }
            });
            // Highlight the new row briefly
            setNewRowIds(prev => {
                const next = new Set(prev);
                next.add(record.id);
                return next;
            });
            setTimeout(() => {
                setNewRowIds(prev => {
                    const next = new Set(prev);
                    next.delete(record.id);
                    return next;
                });
            }, 2500);
        }
    }, [latestMessage]);

    // ── Delete a violation ───────────────────────────────────────────────────
    const handleDelete = async (id) => {
        if (!window.confirm(`Delete violation #${id}?`)) return;
        try {
            const res = await fetch(`${BACKEND_URL}/api/violations/${id}`, {
                method: 'DELETE',
            });
            if (res.ok) {
                setViolations(prev => prev.filter(v => v.id !== id));
                if (onViolationDeleted) onViolationDeleted();
            }
        } catch (err) {
            console.error('Delete failed:', err);
        }
    };

    // ── Delete all violations ────────────────────────────────────────────────
    const handleClearAll = async () => {
        if (!window.confirm(`Are you sure you want to permanently delete ALL violations? This cannot be undone.`)) return;
        try {
            const res = await fetch(`${BACKEND_URL}/api/violations`, {
                method: 'DELETE',
            });
            if (res.ok) {
                setViolations([]);
                if (onClearViolations) onClearViolations();
            }
        } catch (err) {
            console.error('Clear All failed:', err);
        }
    };

    // ── Derived list — search + sort ─────────────────────────────────────────
    const filtered = violations
        .filter(v => {
            if (!searchId.trim()) return true;
            const s = searchId.trim().toLowerCase();
            return (
                String(v.tracker_vehicle_id).includes(s) ||
                (v.vehicle_unique_id && v.vehicle_unique_id.toLowerCase().includes(s))
            );
        })
        .sort((a, b) =>
            sortOrder === 'newest' ? b.id - a.id : a.id - b.id
        );

    // ── Timestamp formatter ──────────────────────────────────────────────────
    const formatTs = (ts) => {
        try {
            return new Date(ts).toLocaleString('en-IN', {
                dateStyle: 'medium',
                timeStyle: 'medium',
            });
        } catch {
            return ts;
        }
    };

    return (
        <div className="violations-page">
            {/* Page Header */}
            <div className="violations-header">
                <h2>
                    🚨 Violations Dashboard
                    <span className="violations-total-badge">{violations.length}</span>
                </h2>
                <span style={{ fontSize: '0.82rem', color: 'var(--text-dim)' }}>
                    <span className="live-dot" />
                    Live updates active
                </span>
            </div>

            {/* Controls */}
            <div className="violations-controls">
                <input
                    type="text"
                    className="violations-search"
                    placeholder="🔍  Search by Vehicle ID…"
                    value={searchId}
                    onChange={e => setSearchId(e.target.value)}
                    id="violations-search-input"
                />

                <select
                    className="violations-sort"
                    value={sortOrder}
                    onChange={e => setSortOrder(e.target.value)}
                    id="violations-sort-select"
                >
                    <option value="newest">Newest First</option>
                    <option value="oldest">Oldest First</option>
                </select>

                <button
                    className="btn-refresh"
                    onClick={fetchViolations}
                    id="violations-refresh-btn"
                    title="Refresh violations list"
                >
                    ↻ Refresh
                </button>
                <button
                    className="btn-clear-all"
                    onClick={handleClearAll}
                    id="violations-clear-all-btn"
                    title="Delete all violations permanently"
                    style={{ backgroundColor: 'var(--alert-color)', color: 'white', border: 'none', marginLeft: 'auto' }}
                >
                    🗑️ Clear All
                </button>
            </div>

            {/* Table / States */}
            {loading ? (
                <div className="violations-loading">
                    <div className="spinner" />
                    <p>Loading violations…</p>
                </div>
            ) : filtered.length === 0 ? (
                <div className="violations-empty">
                    <div className="empty-icon">✅</div>
                    <p>
                        {searchId
                            ? `No violations found for Vehicle ID "${searchId}".`
                            : 'No violations recorded yet. Start processing a video to detect overspeeding vehicles.'}
                    </p>
                </div>
            ) : (
                <div className="violations-table-wrapper">
                    <table className="violations-table" id="violations-data-table">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Video Name</th>
                                <th>Tracker ID</th>
                                <th>Unique ID</th>
                                <th>Vehicle Type</th>
                                <th>Speed</th>
                                <th>Limit</th>
                                <th>Area</th>
                                <th>Timestamp</th>
                                <th>Snapshot</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filtered.map(v => (
                                <tr
                                    key={v.id}
                                    className={newRowIds.has(v.id) ? 'new-row' : ''}
                                >
                                    <td style={{ color: 'var(--text-dim)' }}>{v.id}</td>
                                    <td style={{ maxWidth: 140, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--text-dim)' }} title={v.video_name}>
                                        {v.video_name || '—'}
                                    </td>
                                    <td>
                                        <span className="vehicle-id-chip">
                                            #{v.tracker_vehicle_id}
                                        </span>
                                    </td>
                                    <td>
                                        <span className="vehicle-id-chip" style={{ backgroundColor: '#2a2f35', color: 'var(--text-main)', border: '1px solid #3f4752' }} title={v.vehicle_unique_id}>
                                            {v.vehicle_unique_id}
                                        </span>
                                    </td>
                                    <td>
                                        <span style={{ fontWeight: 500 }}>
                                            {v.vehicle_type || 'Unknown'}
                                        </span>
                                    </td>
                                    <td>
                                        <span className="speed-value">
                                            {v.detected_speed} km/h
                                        </span>
                                    </td>
                                    <td>
                                        <span className="speed-limit-value">
                                            {v.speed_limit} km/h
                                        </span>
                                    </td>
                                    <td>{v.area}</td>
                                    <td style={{ whiteSpace: 'nowrap', color: 'var(--text-dim)', fontSize: '0.82rem' }}>
                                        {formatTs(v.timestamp)}
                                    </td>
                                    <td>
                                        {v.frame_image ? (
                                            <img
                                                className="snapshot-thumb"
                                                src={`data:image/jpeg;base64,${v.frame_image}`}
                                                alt={`Vehicle ${v.vehicle_unique_id} snapshot`}
                                                onClick={() =>
                                                    setLightboxSrc(`data:image/jpeg;base64,${v.frame_image}`)
                                                }
                                                title="Click to enlarge vehicle snapshot"
                                            />
                                        ) : (
                                            <span className="no-snapshot">N/A</span>
                                        )}
                                    </td>
                                    <td>
                                        <button
                                            className="btn-delete-row"
                                            onClick={() => handleDelete(v.id)}
                                            id={`delete-violation-${v.id}`}
                                            title="Delete this violation"
                                        >
                                            Delete
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {/* Lightbox */}
            {lightboxSrc && (
                <div
                    className="lightbox-overlay"
                    onClick={() => setLightboxSrc(null)}
                    role="dialog"
                    aria-label="Vehicle snapshot"
                >
                    <div className="lightbox-inner" onClick={e => e.stopPropagation()}>
                        <img src={lightboxSrc} alt="Vehicle snapshot enlarged" />
                        <button
                            className="lightbox-close"
                            onClick={() => setLightboxSrc(null)}
                            aria-label="Close snapshot"
                        >
                            ✕
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ViolationsDashboard;
