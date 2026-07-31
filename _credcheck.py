import os, json, urllib.request
from dotenv import load_dotenv
load_dotenv()
k = os.environ.get("OPENROUTER_API_KEY")
print("OPENROUTER_API_KEY present:", bool(k), "| prefix:", (k[:14]+"..." if k else None))
for ep in ("https://openrouter.ai/api/v1/auth/key", "https://openrouter.ai/api/v1/credits"):
    try:
        r = urllib.request.Request(ep, headers={"Authorization": f"Bearer {k}"})
        print(f"\n{ep}\n{json.dumps(json.load(urllib.request.urlopen(r, timeout=20)), indent=2)}")
    except Exception as e:
        print(f"\n{ep}\n  ERROR {e}")
