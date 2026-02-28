# 🚦 SmartLight AI
## AI-Powered Intelligent Traffic Management System

SmartLight AI is a full-stack AI-based traffic signal control system that dynamically optimizes traffic flow using real-time vehicle detection and Deep Reinforcement Learning.

This project uses:

- YOLOv8m for real-time vehicle detection
- Deep Q-Network (DQN) for adaptive signal decision making
- FastAPI backend with WebSocket communication
- React + Tailwind frontend dashboard
- Real-time traffic visualization

---

# 📌 Project Overview

Traditional traffic lights operate on fixed timers.

SmartLight AI:

1. Detects vehicles per lane using YOLO
2. Builds a traffic state vector
3. Uses Deep Q-Network to select optimal signal
4. Dynamically adjusts green time
5. Streams real-time updates to dashboard
6. Supports manual override and emergency mode

---

# 🧠 System Architecture


Video Stream
↓
YOLOv8m Detection Service
↓
Lane State Manager
↓
DQN Agent (Decision Engine)
↓
Signal Manager
↓
FastAPI WebSocket Server
↓
React Dashboard


---

# 🏗 Technology Stack

## Backend
- FastAPI
- PyTorch
- Ultralytics YOLOv8m
- OpenCV
- WebSockets (native FastAPI)

## Frontend
- React
- Tailwind CSS
- Chart.js
- WebSocket Client

---

# 📁 Project Structure


SmartLightAI/
│
├── backend/
│ ├── main.py
│ ├── services/
│ │ ├── yolo_service.py
│ │ ├── dqn_agent.py
│ │ ├── signal_manager.py
│ │ ├── state_manager.py
│ │
│ ├── models/
│ │ ├── yolov8m.pt
│ │ └── dqn_model.pth
│ │
│ └── core/
│ └── config.py
│
├── frontend/
│ ├── src/
│ │ ├── components/
│ │ │ ├── Dashboard.jsx
│ │ │ ├── LaneCard.jsx
│ │ │ ├── SignalLight.jsx
│ │ │ └── TrafficChart.jsx
│ │
│ └── package.json
│
└── README.md


---

# ⚙️ Environment Setup

## 1️⃣ Activate Conda Environment


conda activate smartlight


---

## 2️⃣ Backend Dependencies

Installed:

- torch
- ultralytics
- opencv-python
- numpy

Install additional backend requirements:


pip install fastapi uvicorn


---

## 3️⃣ Frontend Setup

Install Node.js (LTS version).

Then:


cd frontend
npm install
npm run dev


---

# 🚀 Running the System

## Start Backend


cd backend
uvicorn main:app --reload


Backend runs at:


http://127.0.0.1:8000


---

## Start Frontend


cd frontend
npm run dev


Frontend runs at:


http://localhost:5173


---

# 🧠 AI Logic

## State Representation


[N_count, S_count, E_count, W_count, current_green_index]


## Action Space


0 → North (N)
1 → South (S)
2 → East (E)
3 → West (W)


## Reward Function


reward = - total_waiting_vehicles


---

# 🚦 Features

- Real-time YOLO vehicle detection
- Deep Reinforcement Learning signal optimization
- WebSocket live updates
- Emergency vehicle override
- Manual override controls
- AI ON/OFF toggle
- Performance metrics dashboard
- Dynamic green time calculation
- Scalable architecture

---

# ⚡ Performance Notes

- YOLOv8m provides higher accuracy but slower inference on CPU.
- Use YOLOv8n for faster performance if required.
- Process every 3rd or 5th frame for optimization.

---

# 🔒 Emergency Handling

If emergency vehicle detected:
- Corresponding lane gets priority
- DQN temporarily paused
- After emergency clearance, AI resumes

---

# 📊 Dashboard Features

- Live vehicle counts per lane
- Signal status indicators
- Countdown timers
- Traffic density chart
- AI performance metrics

---

# 🧪 Future Improvements

- Multi-intersection coordination
- Cloud deployment
- CCTV live feed integration
- Model training dashboard
- Database logging (PostgreSQL / MongoDB)
- Multi-agent reinforcement learning

---

# 🎓 Use Case

- Smart City Traffic Optimization
- AI-based Infrastructure Automation
- Research in Reinforcement Learning
- Final Year Engineering Project

---

# 🏆 Project Status

✔ Professional full-stack architecture  
✔ Real-time AI decision system  
✔ Modular and scalable  
✔ Resume-ready AI project  

---

# 📜 License

This project is developed for educational and research purposes.
