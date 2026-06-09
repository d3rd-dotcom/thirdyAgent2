"""
test_providers.py — Verify all AI providers respond before deploy
Run: python test_providers.py
     python test_providers.py --quick
     python test_providers.py --provider cerebras
"""
import sys, time, requests
from config import (
    CEREBRAS_KEY, NVIDIA_KEY, CF_KEY, CF_ACCOUNT,
    MISTRAL_KEY, COHERE_KEY, GEMINI_KEY, GITHUB_MODELS_KEY,
)

PROMPT  = "Reply with exactly: OK"
SYSTEM  = "You are a test assistant. Follow instructions exactly."
TIMEOUT = 20
QUICK_SKIP = {"github", "cohere"}

TESTS = [
    {"name":"cerebras","label":"Cerebras llama3.1-8b",         "key":CEREBRAS_KEY,      "style":"openai",      "url":"https://api.cerebras.ai/v1/chat/completions",                                         "model":"llama3.1-8b",                    "tier":"REQUIRED"},
    {"name":"nvidia",  "label":"NVIDIA NIM llama-3.1-8b",      "key":NVIDIA_KEY,        "style":"openai",      "url":"https://integrate.api.nvidia.com/v1/chat/completions",                                "model":"meta/llama-3.1-8b-instruct",     "tier":"REQUIRED"},
    {"name":"gemini",  "label":"Gemini 2.0 Flash [Phase8 NEW]","key":GEMINI_KEY,        "style":"gemini",      "url":"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent","model":"gemini-2.0-flash-lite","tier":"PHASE8"},
    {"name":"github",  "label":"GitHub Llama-3.3-70B [Phase8]","key":GITHUB_MODELS_KEY, "style":"openai",      "url":"https://models.inference.ai.azure.com/chat/completions",                              "model":"Llama-3.3-70B-Instruct",         "tier":"PHASE8"},
    {"name":"cloudflare","label":"Cloudflare Workers AI",       "key":CF_KEY,            "style":"cloudflare",  "url":f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT}/ai/run/@cf/meta/llama-3.1-8b-instruct","model":None,           "tier":"OPTIONAL"},
    {"name":"mistral", "label":"Mistral mistral-small",         "key":MISTRAL_KEY,       "style":"openai",      "url":"https://api.mistral.ai/v1/chat/completions",                                          "model":"mistral-small-latest",           "tier":"OPTIONAL"},
    {"name":"cohere",  "label":"Cohere command-r",              "key":COHERE_KEY,        "style":"cohere",      "url":"https://api.cohere.ai/v2/chat",                                                       "model":"command-r",                      "tier":"OPTIONAL"},
]

def test_openai(cfg):
    h = {"Authorization":f"Bearer {cfg['key']}","Content-Type":"application/json"}
    p = {"model":cfg["model"],"messages":[{"role":"system","content":SYSTEM},{"role":"user","content":PROMPT}],"max_tokens":10}
    r = requests.post(cfg["url"],headers=h,json=p,timeout=TIMEOUT)
    if r.status_code==429: return False,"Rate limited 429"
    if r.status_code!=200: return False,f"HTTP {r.status_code}: {r.text[:60]}"
    reply = r.json().get("choices",[{}])[0].get("message",{}).get("content","")
    return bool(reply), reply[:40] or "Empty"

def test_gemini(cfg):
    url = f"{cfg['url']}?key={cfg['key']}"
    p = {"contents":[{"role":"user","parts":[{"text":PROMPT}]}],"generationConfig":{"maxOutputTokens":10}}
    r = requests.post(url,headers={"Content-Type":"application/json"},json=p,timeout=TIMEOUT)
    if r.status_code!=200: return False,f"HTTP {r.status_code}: {r.text[:60]}"
    reply=""
    for c in r.json().get("candidates",[]):
        for part in c.get("content",{}).get("parts",[]):
            reply+=part.get("text","")
    return bool(reply), reply[:40] or "Empty"

def test_cloudflare(cfg):
    h = {"Authorization":f"Bearer {cfg['key']}","Content-Type":"application/json"}
    p = {"messages":[{"role":"system","content":SYSTEM},{"role":"user","content":PROMPT}],"max_tokens":10}
    r = requests.post(cfg["url"],headers=h,json=p,timeout=TIMEOUT)
    if r.status_code!=200: return False,f"HTTP {r.status_code}"
    reply = r.json().get("result",{}).get("response","")
    return bool(reply), reply[:40] or "No result"

def test_cohere(cfg):
    h = {"Authorization":f"Bearer {cfg['key']}","Content-Type":"application/json"}
    p = {"model":cfg["model"],"messages":[{"role":"user","content":PROMPT}],"max_tokens":10}
    r = requests.post(cfg["url"],headers=h,json=p,timeout=TIMEOUT)
    if r.status_code!=200: return False,f"HTTP {r.status_code}"
    reply = r.json().get("message",{}).get("content",[{}])[0].get("text","")
    return bool(reply), reply[:40] or "Empty"

def run(quick=False, only=""):
    print("\n"+"═"*62)
    print("  thirdyAgent2 — AI Provider Health Check  (Phase 8)")
    print("═"*62)
    passed,failed,skipped,no_key=[],[],[],[]
    for cfg in TESTS:
        n,tier,label=cfg["name"],cfg["tier"],cfg["label"]
        if only and n!=only: continue
        if quick and n in QUICK_SKIP:
            skipped.append(n); print(f"  ⏭   {label:<46} SKIPPED (--quick)"); continue
        if not cfg["key"]:
            no_key.append(n)
            icon="⚠️ " if tier=="OPTIONAL" else "❌"
            print(f"  {icon} {label:<46} NO KEY"); continue
        t0=time.time()
        try:
            style=cfg["style"]
            if style=="openai":     ok,msg=test_openai(cfg)
            elif style=="gemini":   ok,msg=test_gemini(cfg)
            elif style=="cloudflare":ok,msg=test_cloudflare(cfg)
            elif style=="cohere":   ok,msg=test_cohere(cfg)
            else:                   ok,msg=False,"unknown style"
        except Exception as e:
            ok,msg=False,str(e)[:60]
        ms=int((time.time()-t0)*1000)
        if ok:
            passed.append(n); print(f"  ✅  {label:<46} OK    ({ms}ms) → {msg}")
        else:
            failed.append(n)
            icon="❌" if tier in ("REQUIRED","PHASE8") else "⚠️ "
            print(f"  {icon} {label:<46} FAIL  ({ms}ms) → {msg}")
    print("\n"+"─"*62)
    print(f"  Passed:{len(passed)}  Failed:{len(failed)}  No-key:{len(no_key)}  Skipped:{len(skipped)}")
    if no_key:  print(f"  No key : {', '.join(no_key)}")
    if skipped: print(f"  Skipped: {', '.join(skipped)}")
    req_failed=[n for n in failed if next((t for t in TESTS if t["name"]==n),{}).get("tier")=="REQUIRED"]
    if req_failed:
        print(f"\n  🚨 REQUIRED providers failed: {req_failed} — fix before deploy\n"); sys.exit(1)
    elif failed:
        print(f"\n  ⚠️  Optional providers failed: {failed} — agent will use fallback chain\n")
    else:
        print("\n  🎉 All tested providers healthy — safe to deploy.\n")

if __name__=="__main__":
    quick = "--quick"    in sys.argv
    only  = next((sys.argv[i+1] for i,a in enumerate(sys.argv) if a=="--provider" and i+1<len(sys.argv)),"")
    run(quick=quick, only=only)
