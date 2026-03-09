import React from 'react';

/**
 * VideoDisplay Component
 * 
 * Displays the processed video feed from the backend.
 * The video frames are received as base64-encoded JPEG images through WebSocket.
 * 
 * When no video is being processed, shows a placeholder message.
 * 
 * @param {string|null} imageSrc - Base64 encoded image data or null
 */
const VideoDisplay = ({ imageSrc, error }) => {
    return (
        <div className="video-container">
            {error ? (
                <div className="video-error-message">
                    <h3>⚠️ Processing Error</h3>
                    <p>{error}</p>
                </div>
            ) : imageSrc ? (
                <img
                    src={imageSrc}
                    alt="Video Stream"
                    className="video-feed"
                />
            ) : (
                <div className="placeholder-text">
                    Select a video and start processing
                </div>
            )}
        </div>
    );
};

export default VideoDisplay;
