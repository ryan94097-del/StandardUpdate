
import json
import scraper
from scraper import check_standard, load_history

def test_ised_only():
    print("Loading history.json...")
    history = load_history()
    ised_standards = history.get("standards", {}).get("ISED", [])
    
    print(f"Found {len(ised_standards)} ISED standards.")
    
    # Filter for RSS-247 specifically for quick verification first, then do others
    # Or just do all ISED as requested. User said "ISED part", implying the category.
    
    for standard in ised_standards:
        # Prioritize RSS-247 for demonstration
        if "RSS-247" in standard['id']:
             print(f"!!! Testing Target: {standard['id']} !!!")
        
        print(f"Testing {standard['id']} ({standard['name']})...")
        try:
            version, date = check_standard(standard)
            if version:
                print(f"  ✓ SUCCESS: {version} (Date: {date})")
                if "RSS-247" in standard['id']:
                    print("  *** RSS-247 VERIFIED ***")
            else:
                print(f"  ✗ FAILED: Unable to fetch version")
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
        print("-" * 30)

if __name__ == "__main__":
    test_ised_only()
