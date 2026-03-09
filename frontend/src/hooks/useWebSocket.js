import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Custom React Hook for WebSocket Connection
 * 
 * This hook manages the WebSocket connection to the backend server.
 * It handles:
 * - Connection establishment and automatic reconnection
 * - Message receiving and parsing
 * - Sending commands to the server
 * - Connection status tracking
 * 
 * @param {string} url - WebSocket server URL
 * @returns {Object} - { isConnected, latestMessage, sendMessage }
 */
const useWebSocket = (url) => {
    const [isConnected, setIsConnected] = useState(false);
    const [latestMessage, setLatestMessage] = useState(null);
    const socketRef = useRef(null);
    const reconnectTimeoutRef = useRef(null);

    // Function to establish WebSocket connection
    const connect = useCallback(() => {
        try {
            // Create new WebSocket connection
            const socket = new WebSocket(url);

            // Connection opened successfully
            socket.onopen = () => {
                console.log('WebSocket Connected');
                setIsConnected(true);
                // Clear any pending reconnection attempts
                if (reconnectTimeoutRef.current) {
                    clearTimeout(reconnectTimeoutRef.current);
                    reconnectTimeoutRef.current = null;
                }
            };

            // Message received from server
            socket.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    setLatestMessage(message);
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error);
                }
            };

            // Connection closed
            socket.onclose = () => {
                console.log('WebSocket Disconnected');
                setIsConnected(false);

                // Only clear ref if this is the current socket
                if (socketRef.current === socket) {
                    socketRef.current = null;
                }

                // Attempt to reconnect after 3 seconds
                reconnectTimeoutRef.current = setTimeout(() => {
                    console.log('Attempting to reconnect...');
                    connect();
                }, 3000);
            };

            // Connection error
            socket.onerror = (error) => {
                console.error('WebSocket Error:', error);
            };

            socketRef.current = socket;
        } catch (error) {
            console.error('Error creating WebSocket:', error);
        }
    }, [url]);

    // Function to send messages through WebSocket
    const sendMessage = useCallback((message) => {
        if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
            socketRef.current.send(JSON.stringify(message));
            return true;
        } else {
            console.warn('WebSocket is not connected');
            return false;
        }
    }, []);

    // Initialize connection on mount
    useEffect(() => {
        connect();

        // Cleanup on unmount
        return () => {
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
            }
            if (socketRef.current) {
                socketRef.current.close();
            }
        };
    }, [connect]);

    return {
        isConnected,
        latestMessage,
        sendMessage
    };
};

export default useWebSocket;
