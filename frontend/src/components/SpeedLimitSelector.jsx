import React, { useState, useEffect } from 'react';
import './SpeedLimitSelector.css';

/**
 * SpeedLimitSelector Component
 * 
 * Allows users to select speed limits either by predefined area or manual input.
 * Manual input overrides area selection.
 * 
 * Features:
 * - Predefined area dropdown (Highway, City, School Zone)
 * - Manual speed limit input with validation
 * - Number-only validation (1-200 km/h)
 * - Real-time feedback
 * 
 * @param {Function} onSpeedLimitChange - Callback when speed limit changes
 * @param {number} defaultLimit - Default speed limit (default: 50)
 */

// Predefined speed limits for different areas
const SPEED_LIMITS = {
    highway: { value: 80, label: 'Highway (80 km/h)' },
    city: { value: 50, label: 'City (50 km/h)' },
    school: { value: 30, label: 'School Zone (30 km/h)' },
    custom: { value: null, label: 'Custom Speed Limit' }
};

const SpeedLimitSelector = ({ onSpeedLimitChange, defaultLimit = 50 }) => {
    const [selectedArea, setSelectedArea] = useState('city');
    const [customSpeed, setCustomSpeed] = useState('');
    const [error, setError] = useState('');

    // Initialize with default limit
    useEffect(() => {
        onSpeedLimitChange(defaultLimit);
    }, []);

    // Handle area selection change
    const handleAreaChange = (e) => {
        const area = e.target.value;
        setSelectedArea(area);
        setError('');

        if (area !== 'custom') {
            // Use predefined area speed limit
            const speedLimit = SPEED_LIMITS[area].value;
            setCustomSpeed('');
            onSpeedLimitChange(speedLimit);
        } else {
            // Switch to custom mode
            if (customSpeed) {
                validateAndSetCustomSpeed(customSpeed);
            }
        }
    };

    // Handle custom speed input change
    const handleCustomSpeedChange = (e) => {
        const value = e.target.value;
        setCustomSpeed(value);

        // Automatically switch to custom mode
        if (selectedArea !== 'custom') {
            setSelectedArea('custom');
        }

        validateAndSetCustomSpeed(value);
    };

    // Validate and set custom speed limit
    const validateAndSetCustomSpeed = (value) => {
        // Allow empty input
        if (value === '') {
            setError('');
            return;
        }

        // Check if input is a number
        const numValue = parseInt(value, 10);

        if (isNaN(numValue)) {
            setError('Please enter a valid number');
            return;
        }

        // Validate range (1-200 km/h)
        if (numValue < 1 || numValue > 200) {
            setError('Speed limit must be between 1-200 km/h');
            return;
        }

        // Valid input
        setError('');
        onSpeedLimitChange(numValue);
    };

    return (
        <div className="speed-limit-selector">
            <label className="speed-limit-label">Speed Limit Configuration</label>

            {/* Area Selection Dropdown */}
            <div className="speed-limit-input-group">
                <label htmlFor="areaSelect" className="input-label">
                    Select Area:
                </label>
                <select
                    id="areaSelect"
                    value={selectedArea}
                    onChange={handleAreaChange}
                    className="speed-limit-dropdown"
                >
                    {Object.entries(SPEED_LIMITS).map(([key, { label }]) => (
                        <option key={key} value={key}>
                            {label}
                        </option>
                    ))}
                </select>
            </div>

            {/* Custom Speed Input */}
            <div className="speed-limit-input-group">
                <label htmlFor="customSpeed" className="input-label">
                    Custom Speed Limit:
                </label>
                <div className="custom-speed-input-wrapper">
                    <input
                        id="customSpeed"
                        type="number"
                        min="1"
                        max="200"
                        value={customSpeed}
                        onChange={handleCustomSpeedChange}
                        placeholder="Enter speed (1-200)"
                        className={`speed-limit-input ${error ? 'error' : ''}`}
                    />
                    <span className="speed-unit">km/h</span>
                </div>
                {error && <div className="speed-limit-error">{error}</div>}
            </div>

            {/* Current Speed Limit Display */}
            <div className="current-speed-display">
                <span className="current-speed-label">Active Limit:</span>
                <span className="current-speed-value">
                    {selectedArea !== 'custom'
                        ? SPEED_LIMITS[selectedArea].value
                        : (customSpeed && !error ? customSpeed : '--')} km/h
                </span>
            </div>
        </div>
    );
};

export default SpeedLimitSelector;
