import sys
import os
import asyncio

# Ensure backend folder is in path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.agent.react_loop import run_agent

# Target expected profiles for verification
expected_profiles = {
    "Zomato": {
        "industry": "food delivery",
        "hq": "gurugram"
    },
    "Stripe": {
        "industry": "fintech",
        "hq": "san francisco"
    },
    "Tata Motors": {
        "industry": "automotive",
        "hq": "mumbai"
    },
    "Notion": {
        "industry": "software",
        "hq": "san francisco"
    },
    "Wave": {
        "industry": "fintech",
        "hq": "dakar"
    }
}

async def run_evaluation():
    print("==========================================================")
    print("  Starting Autonomous Agent QA & Evaluation Suite (V2)")
    print("==========================================================")
    
    failed = False
    results = {}
    
    # Run back-to-back in the same session to verify isolation (no state bleed)
    for company, expectations in expected_profiles.items():
        print(f"\n[RUN] Starting research task for: '{company}'...")
        queue = asyncio.Queue()
        
        try:
            dossier = await run_agent(company, queue)
            results[company] = dossier
            
            # Print basic metadata
            meta = dossier.get("agent_metadata", {})
            print(f"  [OK] Dossier compiled successfully ({meta.get('model_used')}, {meta.get('duration_seconds')}s)")
            
            # Validation assertions
            # 1. Company name validation
            name_val = dossier.get("company", "").strip().lower()
            if company.lower() not in name_val:
                print(f"  [FAIL] Generated company name '{dossier.get('company')}' does not match requested '{company}'")
                failed = True
                continue
                
            # 2. Industry check
            ind_val = dossier.get("industry", "").lower()
            if expectations["industry"] not in ind_val:
                print(f"  [FAIL] Industry '{dossier.get('industry')}' does not match expected keyword '{expectations['industry']}'")
                failed = True
                continue
                
            # 3. Headquarters check
            hq_val = dossier.get("headquarters", "").lower()
            if expectations["hq"] not in hq_val:
                print(f"  [FAIL] Headquarters '{dossier.get('headquarters')}' does not match expected keyword '{expectations['hq']}'")
                failed = True
                continue
                
            # 4. Cross-contamination check (Verify no Razorpay bleed in other companies)
            if company != "Razorpay":
                overview = dossier.get("overview", "")
                if "razorpay" in overview.lower() or "741.5m" in str(dossier).lower():
                    print("  [FAIL] Stale 'Razorpay' details found in the output overview or funding metrics (state bleed detected!)")
                    failed = True
                    continue
            
            print(f"  [PASS] Output data for '{company}' is verified and clean.")
            
        except Exception as e:
            print(f"  [ERROR] Research pipeline failed for '{company}': {str(e)}")
            failed = True
            
    print("\n==========================================================")
    print("  Evaluation Summary:")
    print("==========================================================")
    for company in expected_profiles.keys():
        status_symbol = "PASS" if company in results and not failed else "FAIL/ERROR"
        print(f"  - {company}: {status_symbol}")
    print("==========================================================")
    
    if failed:
        print(" [FAIL] Evaluation Suite Failed. One or more assertions did not pass.")
        sys.exit(1)
    else:
        print(" [SUCCESS] All integration tests passed successfully. V2 Regression closed!")
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(run_evaluation())
