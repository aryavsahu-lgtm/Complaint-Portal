#!/usr/bin/env python3
"""
Quick Performance Test Script
Tests the response times of key endpoints after optimization
"""
import requests
import time

BASE_URL = "http://127.0.0.1:5001"

def test_endpoint(name, url, method='GET', data=None):
    """Test a single endpoint and return response time"""
    try:
        start = time.time()
        
        if method == 'GET':
            response = requests.get(url, timeout=10)
        else:
            response = requests.post(url, json=data, timeout=10)
        
        elapsed = (time.time() - start) * 1000  # Convert to ms
        
        status = "✅" if response.status_code == 200 else "❌"
        print(f"{status} {name:30s} | {elapsed:6.0f}ms | Status: {response.status_code}")
        
        return elapsed
    except Exception as e:
        print(f"❌ {name:30s} | ERROR: {str(e)}")
        return None

def main():
    print("\n" + "="*70)
    print("🚀 Performance Test Report - Smart Complaint System")
    print("="*70 + "\n")
    
    tests = [
        ("Home Page", f"{BASE_URL}/"),
        ("Departments Page", f"{BASE_URL}/departments"),
        ("Login Page", f"{BASE_URL}/auth/login"),
        ("Register Page", f"{BASE_URL}/auth/register"),
        ("Chatbot Page", f"{BASE_URL}/chatbot/"),
    ]
    
    times = []
    
    # Run each test 3 times and average
    for name, url in tests:
        test_times = []
        for i in range(3):
            elapsed = test_endpoint(f"{name} (Test {i+1})", url)
            if elapsed:
                test_times.append(elapsed)
            time.sleep(0.5)  # Brief pause between tests
        
        if test_times:
            avg = sum(test_times) / len(test_times)
            times.append((name, avg))
            print(f"   Average: {avg:.0f}ms\n")
    
    print("="*70)
    print("📊 Summary")
    print("="*70)
    
    for name, avg_time in times:
        rating = "🟢" if avg_time < 300 else "🟡" if avg_time < 800 else "🔴"
        print(f"{rating} {name:30s} | {avg_time:6.0f}ms average")
    
    if times:
        overall_avg = sum(t for _, t in times) / len(times)
        print(f"\n{'Overall Average':30s} | {overall_avg:6.0f}ms")
        
        if overall_avg < 400:
            print("\n✅ EXCELLENT! Performance is optimized.")
        elif overall_avg < 1000:
            print("\n🟡 GOOD. Performance is acceptable but could be improved.")
        else:
            print("\n🔴 SLOW. Performance issues detected.")
    
    print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    print("\n⏳ Starting performance tests...\n")
    time.sleep(1)
    main()
