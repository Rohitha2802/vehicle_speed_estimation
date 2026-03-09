import React, { useEffect, useState } from 'react';
import './DangerAlert.css';

/**
 * DangerAlert Component
 * 
 * Displays a top banner alert when a vehicle exceeds the speed limit.
 * 
 * Features:
 * - Slide-down animation from top
 * - Auto-hide after 5 seconds
 * - Emergency red styling with warning icon
 * - Shows vehicle ID, speed, limit, and violation message
 * 
 * @param {Object} violation - Violation data
 * @param {number} violation.vehicleId - ID of the violating vehicle
 * @param {number} violation.speed - Current speed of vehicle
 * @param {number} violation.speedLimit - Speed limit that was exceeded
 * @param {Function} onClose - Callback when alert closes
 */
const DangerAlert = ({ violation, onClose }) => {
    const [isVisible, setIsVisible] = useState(true);

    useEffect(() => {
        // Auto-hide after 5 seconds
        const timer = setTimeout(() => {
            setIsVisible(false);
            // Wait for animation to complete before calling onClose
            setTimeout(onClose, 300);
        }, 5000);

        return () => clearTimeout(timer);
    }, [onClose]);

    if (!violation) return null;

    return (
        <div className={`danger-alert ${isVisible ? 'slide-in' : 'slide-out'}`}>
            <div className="danger-alert-content">
                <div className="danger-alert-icon">🚨</div>
                <div className="danger-alert-details">
                    <div className="danger-alert-title">OVERSPEED ALERT!</div>
                    <div className="danger-alert-info">
                        <span><strong>Vehicle ID:</strong> {violation.vehicleId}</span>
                        <span><strong>Speed:</strong> {violation.speed} km/h</span>
                        <span><strong>Limit:</strong> {violation.speedLimit} km/h</span>
                    </div>
                    <div className="danger-alert-message">
                        ⚠️ Reporting to nearest police station...
                    </div>
                </div>
                <button
                    className="danger-alert-close"
                    onClick={() => {
                        setIsVisible(false);
                        setTimeout(onClose, 300);
                    }}
                    aria-label="Close alert"
                >
                    ✕
                </button>
            </div>
        </div>
    );
};

export default React.memo(DangerAlert);
