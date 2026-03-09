import React, { useState, useEffect, useCallback, useRef } from 'react';
import './AccidentsDashboard.css';

const BACKEND_URL = 'http://localhost:8000';

/**
 * AccidentsDashboard Component
 *
 * Displays all accident records from the accidents table.
 * Live-updates when the WS pushes accident_detected messages.
 */
const AccidentsDashboard = ({ latestMessage, onClearAccidents, onAccidentDeleted }) => {
    const [accidents, setAccidents] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchId, setSearchId] = useState('');
    const [sortOrder, setSortOrder] = useState('newest');
    const [lightboxSrc, setLightboxSrc] = useState(null);
    const [newRowIds, setNewRowIds] = useState(new Set());
    const prevMessageRef = useRef(null);

    // ── Fetch from REST API ──────────────────────────────────────────────────
    const fetchAccidents = useCallback(async () => {
        setLoading(true);
        try {
            const res = await fetch(`${BACKEND_URL}/api/accidents`);
            if (res.ok) setAccidents(await res.json());
        } catch (err) {
            console.error('Failed to fetch accidents:', err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { fetchAccidents(); }, [fetchAccidents]);

    // ── Real-time WS update ──────────────────────────────────────────────────
    useEffect(() => {
        if (!latestMessage || latestMessage === prevMessageRef.current) return;
        prevMessageRef.current = latestMessage;

        if (latestMessage.accident_detected && latestMessage.accident_event) {
            const record = latestMessage.accident_event;
            setAccidents(prev => {
                const idx = prev.findIndex(a => a.id === record.id);
                if (idx >= 0) {
                    const updated = [...prev];
                    updated[idx] = record;
                    return updated;
                }
                return [record, ...prev];
            });
            setNewRowIds(prev => { const n = new Set(prev); n.add(record.id); return n; });
            setTimeout(() => {
                setNewRowIds(prev => { const n = new Set(prev); n.delete(record.id); return n; });
            }, 2500);
        }
    }, [latestMessage]);

    // ── Delete one record ────────────────────────────────────────────────────
    const handleDelete = async (id) => {
        if (!window.confirm(`Delete accident record #${id}?`)) return;
        try {
            const res = await fetch(`${BACKEND_URL}/api/accidents/${id}`, { method: 'DELETE' });
            if (res.ok) {
                setAccidents(prev => prev.filter(a => a.id !== id));
                if (onAccidentDeleted) onAccidentDeleted();
            }
        } catch (err) { console.error('Delete failed:', err); }
    };

    // ── Delete all records ───────────────────────────────────────────────────
    const handleClearAll = async () => {
        if (!window.confirm('Permanently delete ALL accident records? This cannot be undone.')) return;
        try {
            const res = await fetch(`${BACKEND_URL}/api/accidents`, { method: 'DELETE' });
            if (res.ok) {
                setAccidents([]);
                if (onClearAccidents) onClearAccidents();
            }
        } catch (err) { console.error('Clear all failed:', err); }
    };

    // ── Filter + Sort ────────────────────────────────────────────────────────
    const filtered = accidents
        .filter(a => {
            if (!searchId.trim()) return true;
            const s = searchId.trim().toLowerCase();
            return a.vehicle_ids && a.vehicle_ids.toLowerCase().includes(s);
        })
        .sort((a, b) => sortOrder === 'newest' ? b.id - a.id : a.id - b.id);

    const formatTs = (ts) => {
        try {
            return new Date(ts).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'medium' });
        } catch { return ts; }
    };

    const formatSignals = (sig) => {
        if (!sig) return '—';
        return sig.split(',').map(s => s.trim()).join(' · ');
    };

    const formatVehicles = (ids) => {
        if (!ids) return '—';
        return ids.split(',').map(id => `Vehicle ${id.trim()}`).join(' & ');
    };

    return (
        <div className="accidents-page">
            {/* Header */}
            <div className="accidents-header">
                <h2>
                    💥 Accidents Dashboard
                    <span className="accidents-total-badge">{accidents.length}</span>
                </h2>
                <span style={{ fontSize: '0.82rem', color: 'var(--text-dim)' }}>
                    <span className="live-dot" />Live updates active
                </span>
            </div>

            {/* Controls */}
            <div className="accidents-controls">
                <input
                    type="text"
                    className="accidents-search"
                    placeholder="🔍  Search by Vehicle ID…"
                    value={searchId}
                    onChange={e => setSearchId(e.target.value)}
                    id="accidents-search-input"
                />
                <select
                    className="accidents-sort"
                    value={sortOrder}
                    onChange={e => setSortOrder(e.target.value)}
                    id="accidents-sort-select"
                >
                    <option value="newest">Newest First</option>
                    <option value="oldest">Oldest First</option>
                </select>
                <button className="btn-refresh" onClick={fetchAccidents} id="accidents-refresh-btn" title="Refresh">
                    ↻ Refresh
                </button>
                <button
                    className="btn-clear-all"
                    onClick={handleClearAll}
                    id="accidents-clear-all-btn"
                    style={{ backgroundColor: 'var(--alert-color)', color: 'white', border: 'none', marginLeft: 'auto' }}
                >
                    🗑️ Clear All
                </button>
            </div>

            {/* Table / States */}
            {loading ? (
                <div className="accidents-loading">
                    <div className="spinner" />
                    <p>Loading accident records…</p>
                </div>
            ) : filtered.length === 0 ? (
                <div className="accidents-empty">
                    <div className="empty-icon">✅</div>
                    <p>
                        {searchId
                            ? `No accidents found for Vehicle ID "${searchId}".`
                            : 'No accidents recorded yet. Processing will detect accidents in real-time.'}
                    </p>
                </div>
            ) : (
                <div className="accidents-table-wrapper">
                    <table className="accidents-table" id="accidents-data-table">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Vehicles Involved</th>
                                <th>Frame</th>
                                <th>Area</th>
                                <th>Signals</th>
                                <th>Timestamp</th>
                                <th>Snapshot</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filtered.map(a => (
                                <tr key={a.id} className={newRowIds.has(a.id) ? 'new-row' : ''}>
                                    <td style={{ color: 'var(--text-dim)' }}>{a.id}</td>
                                    <td>
                                        <span className="vehicle-ids-chip">
                                            {formatVehicles(a.vehicle_ids)}
                                        </span>
                                    </td>
                                    <td style={{ color: 'var(--text-dim)', fontFamily: 'monospace' }}>
                                        #{a.frame_number}
                                    </td>
                                    <td>{a.area || '—'}</td>
                                    <td>
                                        {a.signals ? a.signals.split(',').map((s, i) => (
                                            <span key={i} className="signal-chip">{s.trim()}</span>
                                        )) : '—'}
                                    </td>
                                    <td style={{ whiteSpace: 'nowrap', color: 'var(--text-dim)', fontSize: '0.82rem' }}>
                                        {formatTs(a.timestamp)}
                                    </td>
                                    <td>
                                        {a.snapshot ? (
                                            <img
                                                className="snapshot-thumb"
                                                src={`data:image/jpeg;base64,${a.snapshot}`}
                                                alt={`Accident snapshot vehicles ${a.vehicle_ids}`}
                                                onClick={() => setLightboxSrc(`data:image/jpeg;base64,${a.snapshot}`)}
                                                title="Click to enlarge"
                                            />
                                        ) : (
                                            <span className="no-snapshot">N/A</span>
                                        )}
                                    </td>
                                    <td>
                                        <button
                                            className="btn-delete-row"
                                            onClick={() => handleDelete(a.id)}
                                            id={`delete-accident-${a.id}`}
                                            title="Delete this accident record"
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
                    aria-label="Accident snapshot"
                >
                    <div className="lightbox-inner" onClick={e => e.stopPropagation()}>
                        <img src={lightboxSrc} alt="Accident snapshot enlarged" />
                        <button className="lightbox-close" onClick={() => setLightboxSrc(null)} aria-label="Close">✕</button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default AccidentsDashboard;
