# 🛠️ Madeinless:  Autonomous SRE Pipeline

**Sub-Second Remediation | Observability-Driven Logic | Microservices Reliability**

`Madeinless` is an automated Site Reliability Engineering (SRE) pipeline designed to detect, validate, and repair microservice failures. By integrating real-time log analysis with hardware metric correlation, the system achieves a **0.271s MTTR (Mean Time to Repair)**, demonstrating the power of localized, asynchronous self-healing architectures.

---

## 🏗️ System Architecture

The project is built on a closed-loop feedback system, ensuring that every automated action is backed by dual-source verification.

### 📡 1. Infrastructure Layer (`/infra`)
The foundation of the "Digital City" and its monitoring sensors.
* **Target:** Google Online Boutique (10+ microservices) deployed via **Docker Compose**.
* **Observability:** Prometheus (1s scrape interval) and Grafana Loki for near-zero latency telemetry.
* **Chaos Engineering:** Custom scripts to trigger CPU exhaustion, Memory leaks (OOM), and hard service crashes.

### 🧠 2. Remediation Engine (`/engine`)
The "Brain" that processes telemetry and executes "Surgeon" logic.
* **Log Radar (`nlp_engine.py`):** An asynchronous Python listener that scans Loki logs for critical patterns.
* **Telemetry Correlation (`real_telemetry.py`):** Cross-references log events with Prometheus hardware metrics to ensure physical confirmation of a crash.
* **Automated Recovery (`sre_listener.py`):** Communicates with the **Docker Engine SDK** to trigger a container restart the moment a confidence threshold is met.

### 📊 3. Monitoring Dashboard (`/dashboard`)
The "Storyteller" that visualizes the high-speed recovery process.
* **Web Stack:** HTML5, CSS3, and Vanilla JavaScript.
* **Real-time Status:** Visual indicators for service health (Healthy/Crashed/Recovered).
* **SLA Stopwatch:** A high-precision digital timer that tracks the gap between fault injection and successful recovery.

---

## 🚀 Getting Started

### Prerequisites
* Docker & Docker Compose
* Python 3.10+
* A `.env` file containing your `HF_TOKEN` (for Hugging Face API access)

### Installation & Deployment
1. **Clone & Install:**
   ```bash
   git clone [https://github.com/Bhav-05/Madeinless.git](https://github.com/Bhav-05/Madeinless.git)
   cd Madeinless
   pip install -r requirements.txt
   Launch the Pipeline:

2. **Launch the Pipeline**
   ```bash
   cd infra && docker-compose up -d
   Start SRE Logic: cd engine && python sre_listener.py
   Open Dashboard: Open dashboard/index.html in your browser.

**📈 Engineering Highlight: The 0.271s Advantage**

   1.The sub-second MTTR is achieved through Edge-Optimization:
   
   2.Asynchronous I/O: Using aiohttp to ensure the CPU never idles while waiting for data.
   
   3.Direct Socket Access: Commands are sent to the Docker Daemon via local Unix sockets, bypassing cloud API overhead.
   
   4.Precision Correlation: By combining text (logs) and physics (metrics), the system eliminates the "wait-and-see" approach of traditional monitors.
