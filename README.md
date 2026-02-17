# Intelligent Vehicle Monitoring System

A modular Python-based system for real-time vehicle detection, tracking, speed estimation, and behavior analysis using YOLOv8 and DeepSORT.

## Features
- **Vehicle Detection**: Detects cars, bikes, buses, and trucks using YOLOv8.
- **Tracking**: Robust object tracking with DeepSORT.
- **Speed Estimation**: Estimates vehicle speed based on pixel displacement and perspective calibration.
- **Noise Filtering**: Kalman Filter smoothing for stable trajectories.
- **Behavior Analysis**: Detects overspeeding, zig-zag driving, and sudden braking.
- **Risk Prediction**: rudimentary risk scoring based on driving behavior.

## Installation

1.  Clone the repository or download the source.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

1.  Place your input video in the `data/` folder (or use a camera stream index).
2.  Run the main application:
    ```bash
    python main.py --source data/your_video.mp4
    ```

## Project Structure
- `modules/`: Contains all functional modules (detection, tracking, etc.).
- `data/`: Store input videos and models here.
- `main.py`: Main entry point.

## Requirements
- Python 3.8+
- GPU recommended for real-time performance.
