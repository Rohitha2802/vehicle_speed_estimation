import React from 'react';

/**
 * AlertsList Component
 * 
 * Displays a scrollable list of alerts from the vehicle monitoring system.
 * Alerts are displayed in reverse chronological order (newest first).
 * The list is limited to the 20 most recent alerts to prevent memory issues.
 * 
 * Each alert has a slide-in animation when added.
 * 
 * @param {Array<string>} alerts - Array of alert messages
 */
const AlertsList = ({ alerts }) => {
    return (
        <div className="alerts-container">
            <h3>Alerts</h3>
            {alerts.length === 0 ? (
                <div style={{ color: '#666', fontSize: '0.85rem' }}>No alerts yet</div>
            ) : (
                alerts.map((alert, index) => (
                    <div key={index} className="alert-item">
                        {alert}
                    </div>
                ))
            )}
        </div>
    );
};

export default AlertsList;
