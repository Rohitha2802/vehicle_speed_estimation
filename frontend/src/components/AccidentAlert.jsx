import React, { useEffect, useState } from 'react';
import './AccidentAlert.css';

/**
 * AccidentAlert Component
 *
 * Fires when the backend emits `accident_detected: true` on the WebSocket.
 * Visually distinct from the overspeed DangerAlert — orange-red gradient.
 *
 * Props:
 *   accident  – { vehicle_ids, frame_number, area, signals, timestamp }
 *   onClose   – callback when alert is dismissed
 */
const AccidentAlert = ({ accident, onClose }) => {
    const [visible, setVisible] = useState(true);

    useEffect(() => {
        const t = setTimeout(() => {
            setVisible(false);
            setTimeout(onClose, 350);
        }, 8000);
        return () => clearTimeout(t);
    }, [onClose]);

    if (!accident) return null;

    const ids = accident.vehicle_ids
        ? accident.vehicle_ids.split(',').map(s => s.trim()).join(' & ')
        : '—';

    const signals = accident.signals
        ? accident.signals.split(',').map(s => s.trim()).join(', ')
        : '';

    const formatTs = (ts) => {
        try { return new Date(ts).toLocaleTimeString('en-IN'); }
        catch { return ts || '—'; }
    };

    return (
        <div className={`accident-alert ${visible ? 'aa-slide-in' : 'aa-slide-out'}`}>
            <div className="aa-content">
                <div className="aa-icon">💥</div>
                <div className="aa-body">
                    <div className="aa-title">ACCIDENT DETECTED</div>
                    <div className="aa-info">
                        <span><strong>Vehicles:</strong> {ids}</span>
                        <span><strong>Frame:</strong> #{accident.frame_number}</span>
                        <span><strong>Area:</strong> {accident.area || '—'}</span>
                        <span><strong>Time:</strong> {formatTs(accident.timestamp)}</span>
                    </div>
                    {signals && (
                        <div className="aa-signals">⚡ Signals: {signals}</div>
                    )}
                </div>
                <button
                    className="aa-close"
                    onClick={() => { setVisible(false); setTimeout(onClose, 350); }}
                    aria-label="Dismiss accident alert"
                >✕</button>
            </div>
        </div>
    );
};

export default React.memo(AccidentAlert);
