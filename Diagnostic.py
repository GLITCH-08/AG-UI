#!/usr/bin/env python3
"""
Diagnostic script to troubleshoot Azure EventHub connectivity issues
"""

import asyncio
import os
import socket
import sys
from azure.eventhub import EventData
from azure.eventhub.aio import EventHubProducerClient
from azure.core.exceptions import AzureError

# EventHub configuration
EVENTHUB_NAMESPACE = "strat-dev-westus-igoagents-ns-25gliktvxoux6.servicebus.windows.net"
EVENTHUB_NAME = "strat-weather-ingest-igo"
# CONNECTION_STRING = os.environ.get("EVENTHUB_CONNECTION_STRING")
CONNECTION_STRING = "Endpoint=sb://strat-dev-westus-igoagents-ns-25gliktvxoux6.servicebus.windows.net/;SharedAccessKeyName=SendListenKey;SharedAccessKey=DwU3yG7PVDjbe09CYbem1jSbQqxdfLqvL+AEhGtf1sM=;EntityPath=strat-weather-ingest-igo"

def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'=' * 60}")
    print(f"{title}")
    print(f"{'=' * 60}\n")

def check_environment_variable():
    """Check if the connection string is set"""
    print_section("1. Checking Environment Variables")
    
    if CONNECTION_STRING:
        # Mask the sensitive parts
        masked_conn = CONNECTION_STRING[:50] + "..." + CONNECTION_STRING[-20:] if len(CONNECTION_STRING) > 70 else "***"
        print(f"✓ EVENTHUB_CONNECTION_STRING is set")
        print(f"  Length: {len(CONNECTION_STRING)} characters")
        print(f"  Preview: {masked_conn}")
        
        # Parse connection string
        if "Endpoint=" in CONNECTION_STRING and "SharedAccessKeyName=" in CONNECTION_STRING:
            print(f"✓ Connection string format appears valid")
            
            # Extract endpoint
            endpoint = CONNECTION_STRING.split("Endpoint=sb://")[1].split("/;")[0] if "Endpoint=sb://" in CONNECTION_STRING else None
            if endpoint:
                print(f"  Endpoint: {endpoint}")
            
            # Extract key name
            key_name = CONNECTION_STRING.split("SharedAccessKeyName=")[1].split(";")[0] if "SharedAccessKeyName=" in CONNECTION_STRING else None
            if key_name:
                print(f"  Key Name: {key_name}")
                
            # Check if EntityPath is in connection string
            if "EntityPath=" in CONNECTION_STRING:
                entity_path = CONNECTION_STRING.split("EntityPath=")[1].split(";")[0]
                print(f"  Entity Path: {entity_path}")
                if entity_path != EVENTHUB_NAME:
                    print(f"⚠ Warning: EntityPath in connection string ({entity_path}) doesn't match EVENTHUB_NAME ({EVENTHUB_NAME})")
        else:
            print(f"✗ Connection string format may be invalid")
            print(f"  Expected format: Endpoint=sb://...;SharedAccessKeyName=...;SharedAccessKey=...")
            return False
    else:
        print(f"✗ EVENTHUB_CONNECTION_STRING environment variable is not set")
        print(f"  Set it using: export EVENTHUB_CONNECTION_STRING='<your-connection-string>'")
        return False
    
    return True

def check_network_connectivity():
    """Check basic network connectivity to EventHub namespace"""
    print_section("2. Checking Network Connectivity")
    
    hostname = EVENTHUB_NAMESPACE
    ports = [5671, 5672, 443]  # AMQP over TLS, AMQP, HTTPS
    
    print(f"Testing connectivity to: {hostname}\n")
    
    reachable = False
    for port in ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((hostname, port))
            sock.close()
            
            if result == 0:
                print(f"✓ Port {port}: OPEN (reachable)")
                reachable = True
            else:
                print(f"✗ Port {port}: CLOSED or FILTERED")
        except socket.gaierror:
            print(f"✗ Port {port}: DNS resolution failed")
        except socket.timeout:
            print(f"✗ Port {port}: Connection timeout")
        except Exception as e:
            print(f"✗ Port {port}: {type(e).__name__}: {e}")
    
    if not reachable:
        print(f"\n⚠ Warning: No ports are reachable. Check your network/firewall settings.")
        print(f"  EventHub requires port 5671 (AMQP over TLS) or 443 (WebSockets) to be accessible.")
        return False
    
    return True

async def test_connection_with_connection_string():
    """Test connection using connection string"""
    print_section("3. Testing EventHub Connection (Connection String)")
    
    if not CONNECTION_STRING:
        print("✗ Skipping: Connection string not available")
        return False
    
    print(f"Attempting to connect to EventHub: {EVENTHUB_NAME}")
    print(f"Namespace: {EVENTHUB_NAMESPACE}\n")
    
    try:
        # Create producer client
        producer = EventHubProducerClient.from_connection_string(
            conn_str=CONNECTION_STRING,
            eventhub_name=EVENTHUB_NAME,
            logging_enable=True
        )
        
        print("✓ EventHubProducerClient created successfully")
        
        # Try to get properties
        async with producer:
            print("✓ Connection established")
            
            # Try to create a batch (this verifies we can actually communicate)
            event_data_batch = await producer.create_batch()
            print("✓ Can create event batches")
            
            # Try to get partition properties
            try:
                properties = await producer.get_eventhub_properties()
                print(f"✓ Successfully retrieved EventHub properties:")
                print(f"  EventHub name: {properties['eventhub_name']}")
                print(f"  Partition count: {len(properties['partition_ids'])}")
                print(f"  Partition IDs: {properties['partition_ids']}")
            except Exception as prop_error:
                print(f"⚠ Could not retrieve properties: {prop_error}")
            
            print("\n✓ Connection test PASSED")
            return True
            
    except AzureError as e:
        print(f"✗ Azure Error: {e}")
        print(f"  Error type: {type(e).__name__}")
        if hasattr(e, 'error_code'):
            print(f"  Error code: {e.error_code}")
        return False
    except Exception as e:
        print(f"✗ Connection Error: {e}")
        print(f"  Error type: {type(e).__name__}")
        return False

async def test_send_event():
    """Test sending a single event"""
    print_section("4. Testing Event Send")
    
    if not CONNECTION_STRING:
        print("✗ Skipping: Connection string not available")
        return False
    
    try:
        producer = EventHubProducerClient.from_connection_string(
            conn_str=CONNECTION_STRING,
            eventhub_name=EVENTHUB_NAME,
            logging_enable=True
        )
        
        async with producer:
            # Test event sending commented out
            event_data_batch = await producer.create_batch()
            test_event = EventData('{"test": "diagnostic_event", "timestamp": "' + str(asyncio.get_event_loop().time()) + '"}')
            event_data_batch.add(test_event)
            
            print("Sending test event...")
            await producer.send_batch(event_data_batch)
            print("✓ Test event sent successfully!")
            
            print("⚠ Test event sending is disabled. Skipping actual send.")
            return True
            
    except Exception as e:
        print(f"✗ Failed to send test event: {e}")
        print(f"  Error type: {type(e).__name__}")
        return False

def print_recommendations():
    """Print troubleshooting recommendations"""
    print_section("Troubleshooting Recommendations")
    
    print("If tests failed, try these steps:")
    print()
    print("1. Verify Connection String:")
    print("   - Ensure it's from the correct EventHub namespace")
    print("   - Check that the SharedAccessKey is correct and not truncated")
    print("   - Verify the SharedAccessKeyName has 'Send' permissions")
    print()
    print("2. Check Network/Firewall:")
    print("   - Ensure port 5671 (AMQP over TLS) is not blocked")
    print("   - If behind a corporate firewall, port 443 (WebSockets) may work")
    print("   - Try from a different network (e.g., mobile hotspot) to rule out network issues")
    print()
    print("3. Azure Portal Verification:")
    print("   - Confirm the EventHub exists and is active")
    print("   - Check that the namespace is in 'Active' state")
    print("   - Verify the Shared Access Policy has 'Send' permissions")
    print("   - Check for any service health issues in Azure")
    print()
    print("4. Connection String Format:")
    print("   Format: Endpoint=sb://<namespace>.servicebus.windows.net/;SharedAccessKeyName=<key-name>;SharedAccessKey=<key>;EntityPath=<eventhub-name>")
    print("   Note: EntityPath is optional when specifying eventhub_name in code")
    print()
    print("5. Try WebSockets transport:")
    print("   If AMQP (port 5671) is blocked, configure the client to use WebSockets (port 443)")
    print()

async def main():
    """Run all diagnostic tests"""
    print("\n" + "=" * 60)
    print("Azure EventHub Connectivity Diagnostic Tool")
    print("=" * 60)
    
    results = {
        'env_check': False,
        'network_check': False,
        'connection_test': False,
        'send_test': False
    }
    
    # Run tests
    results['env_check'] = check_environment_variable()
    results['network_check'] = check_network_connectivity()
    
    if results['env_check']:
        results['connection_test'] = await test_connection_with_connection_string()
        if results['connection_test']:
            results['send_test'] = await test_send_event()
    
    # Summary
    print_section("Test Summary")
    print(f"Environment Check:  {'✓ PASSED' if results['env_check'] else '✗ FAILED'}")
    print(f"Network Check:      {'✓ PASSED' if results['network_check'] else '✗ FAILED'}")
    print(f"Connection Test:    {'✓ PASSED' if results['connection_test'] else '✗ FAILED'}")
    print(f"Send Event Test:    {'✓ PASSED' if results['send_test'] else '✗ FAILED'}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n" + "=" * 60)
        print("✓ All diagnostics PASSED! Your EventHub connection is working.")
        print("=" * 60)
    else:
        print_recommendations()
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nDiagnostic interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        sys.exit(1)
