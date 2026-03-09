import React from 'react';

/**
 * Header Component
 *
 * Displays the app title, navigation tabs (Monitor / Violations Dashboard),
 * violation count badge, and the WebSocket connection status indicator.
 *
 * @param {boolean}  isConnected      - WebSocket connection status
 * @param {string}   currentPage      - Active page: 'monitor' | 'violations'
 * @param {Function} onNavigate       - Callback when a nav tab is clicked
 * @param {number}   violationsCount  - Total stored violation count (badge)
 */
const Header = ({ isConnected, currentPage, onNavigate, violationsCount }) => {
    return (
        <header className="header">
            <h1>Intelligent Vehicle Monitoring System</h1>

            {/* Navigation Tabs */}
            <nav className="header-nav">
                <button
                    id="nav-monitor"
                    className={`nav-tab ${currentPage === 'monitor' ? 'active' : ''}`}
                    onClick={() => onNavigate('monitor')}
                >
                    📹 Monitor
                </button>
                <button
                    id="nav-violations"
                    className={`nav-tab ${currentPage === 'violations' ? 'active' : ''}`}
                    onClick={() => onNavigate('violations')}
                >
                    🚨 Violations
                    {violationsCount > 0 && (
                        <span className="nav-badge">{violationsCount}</span>
                    )}
                </button>
            </nav>

            {/* Connection Status */}
            <div className="status">
                <span className={`status-indicator ${isConnected ? 'connected' : ''}`} />
                <span>{isConnected ? 'Connected' : 'Disconnected'}</span>
            </div>
        </header>
    );
};

export default Header;
