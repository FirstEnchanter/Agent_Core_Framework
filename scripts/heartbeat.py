import sys
import os

# Add scripts folder to path so we can import guardian
scripts_dir = os.path.dirname(os.path.abspath(__file__))
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)

try:
    import guardian
    print(" Agent Heartbeat: Sending daily status...")
    guardian.log_event(
        event_type="SYSTEM",
        message="Autonomous Systems  Daily Heartbeat",
        detail="All autonomous systems are operational. Guardian is active.",
        level="INFO"
    )
    print(" Heartbeat sent successfully.")
except Exception as e:
    print(f" Heartbeat failed: {e}")
    sys.exit(1)
