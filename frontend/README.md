# Vehicle Monitoring System - React Frontend

This is the React.js frontend for the Intelligent Vehicle Monitoring System.

## 🚀 Quick Start

### Prerequisites
- Node.js (v16 or higher)
- npm (comes with Node.js)
- Backend server running on `http://localhost:8000`

### Installation

1. **Navigate to the frontend directory:**
   ```bash
   cd frontend-react
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Start the development server:**
   ```bash
   npm run dev
   ```

4. **Open your browser:**
   The app will automatically open at `http://localhost:5173`

## 📁 Project Structure

```
frontend-react/
├── src/
│   ├── components/          # React components
│   │   ├── Header.jsx       # App header with connection status
│   │   ├── Sidebar.jsx      # Controls and stats sidebar
│   │   ├── VideoDisplay.jsx # Video feed display
│   │   ├── StatsPanel.jsx   # Live statistics
│   │   └── AlertsList.jsx   # Alerts display
│   ├── hooks/
│   │   └── useWebSocket.js  # WebSocket connection hook
│   ├── App.jsx              # Main application component
│   ├── App.css              # Component styles
│   ├── main.jsx             # React entry point
│   └── index.css            # Global styles
├── public/                  # Static assets
├── index.html               # HTML entry point
├── package.json             # Dependencies
└── vite.config.js           # Vite configuration
```

## 🎯 Features

- **Real-time Video Processing**: Live video feed with vehicle detection
- **WebSocket Communication**: Automatic connection and reconnection
- **Live Statistics**: FPS and vehicle count tracking
- **Alert System**: Real-time violation alerts
- **Modern UI**: Dark theme with smooth animations
- **Responsive Design**: Works on different screen sizes

## 🔧 Available Scripts

- `npm run dev` - Start development server with hot reload
- `npm run build` - Build production bundle
- `npm run preview` - Preview production build locally

## 🌐 Backend Connection

The frontend connects to:
- **HTTP API**: `http://localhost:8000` (for file uploads)
- **WebSocket**: `ws://localhost:8000/ws` (for real-time data)

Make sure the backend server is running before starting the frontend.

## 📝 How to Use

1. **Upload Video**: Click "Select Video" and choose a video file
2. **Start Processing**: Click "Start Processing" to begin analysis
3. **View Results**: Watch the processed video feed with vehicle detection
4. **Monitor Stats**: Check FPS and active vehicle count in real-time
5. **Check Alerts**: View violation alerts as they occur
6. **Stop Processing**: Click "Stop" to end processing

## 🎨 Customization

### Changing Colors
Edit the CSS variables in `src/index.css`:
```css
:root {
  --bg-color: #121212;
  --surface-color: #1e1e1e;
  --primary-color: #00e676;
  --secondary-color: #2979ff;
  --alert-color: #ff1744;
}
```

### Changing Backend URL
Edit the constants in `src/App.jsx`:
```javascript
const BACKEND_URL = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000/ws';
```

## 🐛 Troubleshooting

**Issue**: "WebSocket not connected"
- **Solution**: Ensure backend server is running on port 8000

**Issue**: "Upload failed"
- **Solution**: Check backend server logs and ensure upload endpoint is working

**Issue**: npm install fails
- **Solution**: Delete `node_modules` and `package-lock.json`, then run `npm install` again

## 📦 Dependencies

- **react** (^18.2.0) - UI library
- **react-dom** (^18.2.0) - React DOM rendering
- **vite** (^5.0.8) - Build tool and dev server
- **@vitejs/plugin-react** (^4.2.1) - Vite React plugin

## 🔄 Migration from Vanilla JS

This React version replaces the old `frontend/` directory which used:
- Static HTML (`index.html`)
- Vanilla JavaScript (`app.js`)
- Python HTTP server

The new React version provides:
- Component-based architecture
- Better state management
- Hot module replacement
- Modern development experience
- Easier maintenance and testing
