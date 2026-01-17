import requests
import sys

API_BASE = "http://localhost:8000"

def get_open_alerts():
    """Fetch all open alerts."""
    try:
        response = requests.get(f"{API_BASE}/alerts?status=open")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching alerts: {e}")
        return []

def resolve_alert(alert_id):
    """Resolve an alert by ID."""
    try:
        url = f"{API_BASE}/alerts/{alert_id}/resolve"
        print(f"Sending POST request to: {url}")
        
        response = requests.post(url)
        
        if response.status_code == 200:
            print(f"✅ Alert {alert_id} successfully resolved!")
            return True
        elif response.status_code == 404:
            print(f"❌ Alert {alert_id} not found.")
        elif response.status_code == 400:
            print(f"⚠️ Alert {alert_id} is already resolved.")
        else:
            print(f"❌ Failed to resolve alert: {response.text}")
            
    except Exception as e:
        print(f"Error resolving alert: {e}")
    return False

if __name__ == "__main__":
    print("--- DeFi Monitor Alert Resolver ---")
    
    # 1. Fetch current alerts
    alerts = get_open_alerts()
    
    if not alerts:
        print("No open alerts found.")
        sys.exit(0)
        
    print(f"\nFound {len(alerts)} open alerts:")
    print(f"{'ID':<5} {'PROTOCOL':<10} {'SEVERITY':<10} {'MESSAGE'}")
    print("-" * 60)
    
    for alert in alerts:
        print(f"{alert['id']:<5} {alert['protocol_name']:<10} {alert['severity']:<10} {alert['message'][:50]}...")
    
    # 2. Ask user for ID
    if len(sys.argv) > 1:
        target_id = sys.argv[1]
    else:
        print("\n")
        target_id = input("Enter Alert ID to resolve (or 'q' to quit): ")
    
    if target_id.lower() == 'q':
        sys.exit(0)
        
    try:
        alert_id = int(target_id)
        resolve_alert(alert_id)
    except ValueError:
        print("Invalid ID. Please enter a number.")
