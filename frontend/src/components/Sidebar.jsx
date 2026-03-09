import React, { useRef } from 'react';
import StatsPanel from './StatsPanel';
import AlertsList from './AlertsList';
import SpeedLimitSelector from './SpeedLimitSelector';

/**
 * Sidebar Component
 * 
 * Contains all the controls and information panels:
 * - File upload button and selected file name
 * - Speed limit selector (area-based or manual)
 * - Start/Stop processing buttons
 * - Live statistics panel (FPS, vehicle count)
 * - Alerts list
 * 
 * This component manages the file upload UI and delegates button actions
 * to parent component handlers.
 * 
 * @param {Function} onFileSelect - Callback when file is selected
 * @param {Function} onStartProcessing - Callback to start video processing
 * @param {Function} onStopProcessing - Callback to stop processing
 * @param {Function} onSpeedLimitChange - Callback when speed limit changes
 * @param {string} fileName - Name of selected file
 * @param {boolean} canStart - Whether start button should be enabled
 * @param {boolean} isProcessing - Whether video is currently being processed
 * @param {number} fps - Current FPS value
 * @param {number} vehicleCount - Current vehicle count
 * @param {Array<string>} alerts - Array of alert messages
 * @param {number} speedLimit - Current speed limit value
 */
const Sidebar = ({
    onFileSelect,
    onStartProcessing,
    onStopProcessing,
    onSpeedLimitChange,
    fileName,
    canStart,
    isProcessing,
    fps,
    vehicleCount,
    alerts,
    speedLimit
}) => {
    const fileInputRef = useRef(null);

    const handleFileClick = () => {
        fileInputRef.current?.click();
    };

    const handleFileChange = (e) => {
        const file = e.target.files[0];
        if (file) {
            onFileSelect(file);
        }
    };

    return (
        <aside className="sidebar">
            {/* File Upload Section */}
            <div className="control-group">
                <label htmlFor="videoInput">Upload Video</label>
                <input
                    ref={fileInputRef}
                    type="file"
                    id="videoInput"
                    accept="video/*"
                    onChange={handleFileChange}
                    className="hidden-input"
                />
                <button className="btn-upload" onClick={handleFileClick}>
                    Select Video
                </button>
                <span className="file-name">
                    {fileName || 'No file selected'}
                </span>
            </div>

            {/* Speed Limit Selector */}
            <SpeedLimitSelector
                onSpeedLimitChange={onSpeedLimitChange}
                defaultLimit={speedLimit}
            />

            {/* Control Buttons */}
            <div className="control-group">
                <button
                    className="btn-start"
                    onClick={onStartProcessing}
                    disabled={!canStart || isProcessing}
                >
                    Start Processing
                </button>
                <button
                    className="btn-stop"
                    onClick={onStopProcessing}
                    disabled={!isProcessing}
                >
                    Stop
                </button>
            </div>

            {/* Stats Panel */}
            <StatsPanel fps={fps} vehicleCount={vehicleCount} />

            {/* Alerts List */}
            <AlertsList alerts={alerts} />
        </aside>
    );
};

export default Sidebar;
