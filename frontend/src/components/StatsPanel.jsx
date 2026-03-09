import React from 'react';

/**
 * StatsPanel Component
 * 
 * Displays real-time statistics from the video processing:
 * - FPS (Frames Per Second): Processing speed
 * - Active Vehicles: Number of vehicles currently detected
 * 
 * These values are updated in real-time from WebSocket messages.
 * 
 * @param {number} fps - Current frames per second
 * @param {number} vehicleCount - Number of active vehicles detected
 */
const StatsPanel = ({ fps, vehicleCount }) => {
    return (
        <div className="stats-panel">
            <h3>Live Stats</h3>
            <div className="stat-item">
                <span>FPS:</span>
                <span className="stat-value">{fps.toFixed(1)}</span>
            </div>
            <div className="stat-item">
                <span>Active Vehicles:</span>
                <span className="stat-value">{vehicleCount}</span>
            </div>
        </div>
    );
};

export default StatsPanel;
