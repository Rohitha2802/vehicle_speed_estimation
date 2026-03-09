# Intelligent Vehicle Monitoring System

A modular Python-based system for real-time vehicle detection, tracking, speed estimation, and behavior analysis using YOLOv8 and DeepSORT. This system supports both a Command Line Interface (CLI) for processing video files and a Web Interface for real-time interaction.

## Features
- **Vehicle Detection**: Detects cars, bikes, buses, and trucks using YOLOv8.
- **Tracking**: Robust object tracking with DeepSORT.
- **Speed Estimation**: Estimates vehicle speed based on pixel displacement and perspective calibration.
- **Noise Filtering**: Kalman Filter smoothing for stable trajectories.
- **Behavior Analysis**: Detects overspeeding, zig-zag driving, and sudden braking.
- **Risk Prediction**: rudimentary risk scoring based on driving behavior.

## Project Structure
- `backend/`: Contains the FastAPI backend and core logic modules.
  - `modules/`: Functional modules for detection, tracking, speed estimation, etc.
  - `uploads/`: Directory where uploaded videos are stored.
  - `main.py`: FastAPI application entry point.
- `frontend/`: Contains the web interface files (`index.html`, `app.js`, `style.css`).
- `data/`: Directory to store input videos and models.
- `main.py`: CLI entry point for processing videos directly.

## Prerequisites
- Python 3.8+
- pip (Python package installer)
- GPU recommended for real-time performance.

## Installation

1.  Clone the repository or download the source code.
2.  Navigate to the project root directory.
3.  Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

### 1. Command Line Interface (CLI)
Use the CLI to process a video file directly and view the output in a window.

```bash
python main.py --source data/your_video.mp4
```
*Note: Replace `data/your_video.mp4` with the path to your input video.*

**Arguments:**
- `--source`: Path to the video file or camera index (default: `data/test_video.mp4`).
- `--model`: Path to the YOLOv8 model file (default: `yolov8n.pt`).

### 2. Web Interface
Use the Web Interface to upload videos and view the processing results in a browser.

**Step 1: Start the Backend Server**
Run the following command from the project root:
```bash
uvicorn backend.main:app --reload
```
This will start the FastAPI server at `http://127.0.0.1:8000`.

**Step 2: Start the Frontend**
Simply open the `frontend/index.html` file in your web browser. You can do this by double-clicking the file or dragging it into your browser window.

**Step 3: Upload and Process**
1.  In the web interface, click "Choose File" and select a video.
2.  Click "Start Processing" to begin the analysis.
3.  The processed video feed, vehicle counts, and alerts will appear in real-time.

## Troubleshooting

- **ModuleNotFoundError**: Ensure you are running commands from the project root directory so that python can find the `backend` and `modules` packages.
- **WebSocket Disconnected**: Make sure the backend server (`uvicorn`) is running before opening the frontend.
- **Video Not Found**: If using CLI, ensure the path provided to `--source` is correct.
