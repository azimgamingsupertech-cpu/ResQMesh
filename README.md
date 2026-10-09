# ResQMesh — Offline Disaster Response and SOS System

**OPCODE IMPACT 2026 | Hackathon Submission**

**Team ID:** OPC014

## 1. Problem Statement

During natural disasters and other emergencies, mobile internet and conventional communication networks may become unavailable or unreliable. This can prevent people from requesting help and make it difficult for rescue teams to identify and prioritize people in need.

## 2. Solution Title

**ResQMesh — Offline-First Emergency SOS and Disaster Response System**

## 3. Solution Description

ResQMesh is a disaster-response project designed to help people create emergency SOS alerts and share essential information with a response dashboard. It includes a mobile-friendly SOS interface, location support, and local storage for emergency messages when delivery fails. The project aims to support communication during network disruptions and provide a centralized interface for viewing received alerts. Future development will focus on enabling device-to-device SOS delivery without internet access.

## 4. Architecture Diagram

_Add your architecture diagram at `docs/architecture.png`._

**Workflow:** A user creates an SOS message through the mobile interface. The application stores the message locally and attempts to deliver it to the ResQMesh laptop server. Successfully received alerts can be processed and displayed on the response dashboard. Pending messages require a working communication path before they can be delivered.

## 5. Technology Stack

- **Frontend:** HTML, CSS, JavaScript
- **Backend:** Python, Flask
- **Database:** SQLite
- **Other Technologies:** Browser geolocation, IndexedDB for local SOS storage, Streamlit for the response dashboard

## 6. Quick Start Guide

**Prerequisites:**

- Python 3
- A laptop running Windows, Linux, or macOS
- An Android phone or compatible browser
- Python dependencies required by the project

**Installation & Execution:**

Clone your public repository and open the project directory:

```bash
git clone <YOUR_PUBLIC_GITHUB_REPOSITORY_URL>
cd ResQMesh
```

Install the required dependencies for your project. At minimum, the mobile SOS server uses Flask and the dashboard uses Streamlit:

```bash
pip install flask streamlit
```

Run the mobile SOS server:

```bash
python resqmesh_mobile_sos_offline_storage.py
```

Open the mobile interface using the laptop's reachable local IP address and port `5001`:

```text
http://<LAPTOP_LOCAL_IP>:5001
```

Run the dashboard separately using the appropriate dashboard script:

```bash
streamlit run app_resqmesh_cyan_black.py
```

**Note:** Confirm all required Python dependencies and setup instructions before publishing this guide.

## 7. Output Screenshots

_Add genuine screenshots to `docs/output.png` showing the mobile SOS interface and the response dashboard._

The screenshots should demonstrate the current implementation. Do not use placeholder or illustrative images as proof of working features.

## 8. Future Scope

- Implement and test reliable SOS delivery between devices without internet access.
- Explore Bluetooth-based device-to-device communication and message relaying.
- Add automatic retry and synchronization for pending SOS messages.
- Improve location sharing, alert prioritization, and rescue-team coordination.
- Test the system under simulated network outages and disaster scenarios.

## 9. Team Contributions

| Member Name | Contribution |
|---|---|
| Mohamed Anas | Project concept, system design, and frontend |
| Sathyaseelan | Support throughout the project development |

## 10. Tools Used

| Tool / Platform | Purpose / Why Used |
|---|---|
| Python | Backend development |
| Flask | SOS server and request handling |
| SQLite | Local database storage |
| Streamlit | Emergency response dashboard |
| GitHub | Source control and project submission |
| ChatGPT | Assistance with planning, debugging, documentation, and development |
