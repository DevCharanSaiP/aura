"""
Test script for the complete booking lifecycle:
1. Propose slots for a vehicle
2. Confirm a booking
3. Verify slot is not suggested again
4. Verify booking appears in upcoming list
"""

import requests
import json
from datetime import datetime, timedelta

API_BASE = "http://127.0.0.1:8000"
SCHEDULING_BASE = "http://127.0.0.1:8300"

def test_booking_lifecycle():
    vehicle_id = "V001"
    
    print("=" * 60)
    print("AURA BOOKING LIFECYCLE TEST")
    print("=" * 60)
    
    # Step 1: Propose slots
    print("\n[Step 1] Proposing slots for", vehicle_id)
    schedule_res = requests.post(
        f"{SCHEDULING_BASE}/propose_slots",
        json={"vehicle_id": vehicle_id, "owner_name": "Test User"},
        timeout=5
    )
    schedule_data = schedule_res.json()
    print(f"✓ Response: {schedule_data['can_schedule']}")
    print(f"  Total suggested: {schedule_data.get('total_suggested', 'N/A')}")
    print(f"  Available: {schedule_data.get('available', 'N/A')}")
    
    if not schedule_data.get("can_schedule"):
        print("❌ Cannot schedule - skipping test")
        return
    
    first_slot = schedule_data["options"][0]
    print(f"✓ First slot: {first_slot['label']}")
    
    # Step 2: Confirm booking
    print(f"\n[Step 2] Confirming booking for {first_slot['label']}")
    confirm_res = requests.post(
        f"{API_BASE}/bookings/confirm",
        json={
            "vehicle_id": vehicle_id,
            "slot_start": first_slot["start"],
            "slot_end": first_slot["end"],
            "center_id": "TEST_CENTER"
        },
        timeout=5
    )
    booking_data = confirm_res.json()
    if booking_data.get("success"):
        booking_id = booking_data.get("booking_id")
        print(f"✓ Booking confirmed! ID: {booking_id}")
        print(f"  Status: {booking_data.get('status')}")
        print(f"  Confirmed at: {booking_data.get('confirmed_at')}")
    else:
        print(f"❌ Booking failed: {booking_data.get('error')}")
        return
    
    # Step 3: Propose slots again - should exclude booked slot
    print(f"\n[Step 3] Proposing slots again - booked slot should be unavailable")
    schedule_res2 = requests.post(
        f"{SCHEDULING_BASE}/propose_slots",
        json={"vehicle_id": vehicle_id, "owner_name": "Test User"},
        timeout=5
    )
    schedule_data2 = schedule_res2.json()
    print(f"✓ Response: {schedule_data2['can_schedule']}")
    print(f"  Total suggested: {schedule_data2.get('total_suggested', 'N/A')}")
    print(f"  Available: {schedule_data2.get('available', 'N/A')}")
    
    # Check if booked slot was filtered out
    booked_slot_found = False
    for opt in schedule_data2.get("options", []):
        if opt["start"] == first_slot["start"]:
            booked_slot_found = True
            break
    
    if booked_slot_found:
        print(f"❌ FAIL: Booked slot still appears in suggestions!")
    else:
        print(f"✓ PASS: Booked slot correctly filtered from suggestions")
    
    # Step 4: Check upcoming bookings
    print(f"\n[Step 4] Checking upcoming bookings")
    bookings_res = requests.get(f"{API_BASE}/bookings/upcoming", timeout=5)
    bookings_data = bookings_res.json()
    
    booking_found = False
    for booking in bookings_data.get("bookings", []):
        if booking["vehicle_id"] == vehicle_id and booking["booking_id"] == booking_id:
            booking_found = True
            print(f"✓ Booking found in upcoming list")
            print(f"  Vehicle: {booking['vehicle_id']}")
            print(f"  Time: {booking['slot_start']}")
            print(f"  Status: {booking['status']}")
            break
    
    if not booking_found:
        print(f"❌ FAIL: Booking not found in upcoming list")
    else:
        print(f"✓ PASS: Booking correctly appears in upcoming bookings")
    
    print("\n" + "=" * 60)
    print("✅ BOOKING LIFECYCLE TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_booking_lifecycle()
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
