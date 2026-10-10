ResQMesh Android Mobile SOS — same local Wi-Fi only

WHAT THIS DOES
- Serves a phone-friendly cyan/black SOS page from your laptop.
- Sends the SOS directly to the laptop over your local Wi-Fi; no cloud or internet message service is used.
- Saves incoming SOS messages in resqmesh.db in both offline_messages (SOS inbox) and alerts (dashboard incidents).
- Stores a message in the phone browser's pending queue if delivery fails, and lets you retry.

SETUP
1. Copy resqmesh_mobile_sos.py into the SAME Documents\ResQMesh folder that contains your final app_resqmesh_cyan_black.py and resqmesh.db.
2. Open Command Prompt in that folder.
3. Install Flask once if needed:
      py -m pip install flask
   If `py` is not available, try `python -m pip install flask`.
4. Start the existing laptop dashboard in its own terminal as usual.
5. Open a SECOND terminal in the same ResQMesh folder and run:
      py resqmesh_mobile_sos.py
   or:
      python resqmesh_mobile_sos.py
6. The terminal prints local addresses. On the Android phone connected to the same Wi-Fi, open the address printed with the laptop's LAN IP, e.g. http://192.168.x.x:5000.
7. If Windows Firewall asks, allow Python on Private networks only. Do not expose port 5000 to public networks.
8. Send a clearly labelled test message first and verify it appears in the laptop's Incoming Offline SOS Messages and incident list.

IMPORTANT NOTES
- Keep the mobile service terminal open while using the phone interface.
- The phone and laptop must be on the same reachable Wi-Fi/LAN. Some guest Wi-Fi networks isolate devices; use a network that permits device-to-device traffic.
- If the laptop IP changes, use the newly printed address.
- Browser GPS can be blocked on a plain HTTP local-network address. If so, type a landmark or coordinates manually. Do not assume the location is accurate unless the phone shows it.
- A message can only be delivered when the phone can reach the laptop. The local browser queue is a retry queue, not a Bluetooth/off-grid mesh.
- This is a hackathon prototype, not a certified emergency service. Do not rely on it for real-life rescue.
