import { useState, useEffect, useRef, useCallback } from 'react';
import './App.css';
import useWebSocket from './hooks/useWebSocket';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import VideoDisplay from './components/VideoDisplay';
import DangerAlert from './components/DangerAlert';
import ViolationsDashboard from './components/ViolationsDashboard';

// Backend configuration
const BACKEND_URL = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000/ws';

function App() {
    // WebSocket connection
    const { isConnected, latestMessage, sendMessage } = useWebSocket(WS_URL);

    // ── Page routing ─────────────────────────────────────────────────────────
    const [currentPage, setCurrentPage] = useState('monitor'); // 'monitor' | 'violations'
    const [violationsCount, setViolationsCount] = useState(0);

    // Fetch total violations count on mount so the badge is pre-populated
    useEffect(() => {
        fetch(`${BACKEND_URL}/api/violations`)
            .then(r => r.json())
            .then(data => setViolationsCount(data.length))
            .catch(() => { });
    }, []);

    // ── Application state ────────────────────────────────────────────────────
    const [selectedFile, setSelectedFile] = useState(null);
    const [uploadedFilename, setUploadedFilename] = useState(null);
    const [isProcessing, setIsProcessing] = useState(false);
    const [videoSrc, setVideoSrc] = useState(null);
    const [fps, setFps] = useState(0);
    const [vehicleCount, setVehicleCount] = useState(0);
    const [alerts, setAlerts] = useState([]);

    // Speed limit alert system state
    const [speedLimit, setSpeedLimit] = useState(50);
    const [currentViolation, setCurrentViolation] = useState(null);
    const alertCooldowns = useRef({});
    const [errorMessage, setErrorMessage] = useState(null);

    /**
     * Check for speed violations and show the danger alert banner.
     * Implements a 10-second cooldown per vehicle to prevent spam.
     */
    const checkSpeedViolations = useCallback((vehicles) => {
        const now = Date.now();
        for (const vehicle of vehicles) {
            if (vehicle.violation && vehicle.speed && vehicle.id !== undefined) {
                const vehicleId = vehicle.id;
                const lastAlertTime = alertCooldowns.current[vehicleId] || 0;
                if (now - lastAlertTime > 10000) {
                    alertCooldowns.current[vehicleId] = now;
                    setCurrentViolation({
                        vehicleId: vehicleId,
                        speed: Math.round(vehicle.speed),
                        speedLimit: vehicle.speed_limit || speedLimit,
                    });
                    console.log(`🚨 Speed violation: Vehicle ${vehicleId} at ${vehicle.speed} km/h`);
                    break; // Show one alert at a time
                }
            }
        }
    }, [speedLimit]);

    /**
     * Handle incoming WebSocket messages.
     */
    useEffect(() => {
        if (!latestMessage) return;

        if (latestMessage.status === 'complete' || latestMessage.status === 'finished') {
            console.log('Processing Complete');
            setIsProcessing(false);
            return;
        }

        if (latestMessage.error) {
            console.error('Backend Error:', latestMessage.error);
            setErrorMessage(latestMessage.error);
            setIsProcessing(false);
            return;
        }

        if (latestMessage.image) {
            setVideoSrc('data:image/jpeg;base64,' + latestMessage.image);

            if (latestMessage.fps !== undefined) {
                setFps(parseFloat(latestMessage.fps) || 0);
            }

            if (latestMessage.vehicles) {
                setVehicleCount(latestMessage.vehicles.length);
                checkSpeedViolations(latestMessage.vehicles);
            }

            if (latestMessage.alerts && latestMessage.alerts.length > 0) {
                setAlerts(prevAlerts => {
                    const newAlerts = [...latestMessage.alerts, ...prevAlerts];
                    return newAlerts.slice(0, 20);
                });
            }

            // A new violation was saved by the backend
            if (latestMessage.violation_saved) {
                // Only increment the badge count if it's a completely new vehicle record (not an update)
                if (latestMessage.violation_action === 'inserted') {
                    setViolationsCount(prev => prev + 1);
                }
            }
        }
    }, [latestMessage, checkSpeedViolations]);

    // ── Event handlers ───────────────────────────────────────────────────────

    const handleCloseAlert = () => setCurrentViolation(null);

    const handleSpeedLimitChange = (newLimit) => {
        setSpeedLimit(newLimit);
        console.log('Speed limit updated to:', newLimit, 'km/h');
    };

    const handleFileSelect = async (file) => {
        setSelectedFile(file);
        const formData = new FormData();
        formData.append('file', file);
        try {
            const response = await fetch(`${BACKEND_URL}/upload`, {
                method: 'POST',
                body: formData,
            });
            const result = await response.json();
            if (response.ok) {
                setUploadedFilename(result.filename);
                console.log('Upload successful:', result.filename);
            } else {
                alert('Upload failed: ' + (result.detail || 'Unknown error'));
                setSelectedFile(null);
            }
        } catch (error) {
            console.error('Error uploading file:', error);
            alert('Error uploading file. Please try again.');
            setSelectedFile(null);
        }
    };

    const handleStartProcessing = () => {
        if (!isConnected) {
            alert('WebSocket not connected. Please wait for connection.');
            return;
        }
        if (!uploadedFilename) {
            alert('Please upload a video first');
            return;
        }
        setVideoSrc(null);
        setVehicleCount(0);
        setFps(0);
        setAlerts([]);
        setErrorMessage(null);

        const success = sendMessage({
            command: 'start',
            filename: uploadedFilename,
            speed_limit: speedLimit,
        });

        if (success) {
            setIsProcessing(true);
            setAlerts([]);
            alertCooldowns.current = {};
            setCurrentViolation(null);
            console.log('Started processing:', uploadedFilename, 'with speed limit:', speedLimit, 'km/h');
        } else {
            console.error('Failed to send start command.');
            alert('Connection/Socket Error: Failed to send command. Please refresh the page.');
            setIsProcessing(false);
        }
    };

    const handleStopProcessing = () => {
        window.location.reload();
    };

    // ── Render ───────────────────────────────────────────────────────────────
    return (
        <div className="app-container">
            {/* Header — with navigation tabs */}
            <Header
                isConnected={isConnected}
                currentPage={currentPage}
                onNavigate={setCurrentPage}
                violationsCount={violationsCount}
            />

            {/* Page: Monitor */}
            {currentPage === 'monitor' && (
                <main className="main-content">
                    <Sidebar
                        onFileSelect={handleFileSelect}
                        onStartProcessing={handleStartProcessing}
                        onStopProcessing={handleStopProcessing}
                        onSpeedLimitChange={handleSpeedLimitChange}
                        fileName={selectedFile?.name}
                        canStart={!!uploadedFilename && isConnected}
                        isProcessing={isProcessing}
                        fps={fps}
                        vehicleCount={vehicleCount}
                        alerts={alerts}
                        speedLimit={speedLimit}
                    />
                    <VideoDisplay imageSrc={videoSrc} error={errorMessage} />
                </main>
            )}

            {/* Page: Violations Dashboard */}
            {currentPage === 'violations' && (
                <div className="violations-content">
                    <ViolationsDashboard
                        latestMessage={latestMessage}
                        onClearViolations={() => setViolationsCount(0)}
                        onViolationDeleted={() => setViolationsCount(prev => Math.max(0, prev - 1))}
                    />
                </div>
            )}
        </div>
    );
}

export default App;
