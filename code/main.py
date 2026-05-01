import os, csv, json, pathlib, time
from groq import Groq

BASE_DIR   = pathlib.Path(__file__).resolve().parent.parent
DATA_DIR   = BASE_DIR / "data"
TICKETS_IN = BASE_DIR / "support_tickets" / "support_tickets.csv"
OUTPUT_CSV = BASE_DIR / "support_tickets" / "output.csv"

LOG_FILE = BASE_DIR / "log.txt"

def log_write(text):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(text + "\n")
# ───────── CLEAN TEXT ─────────
def clean(text):
    if not text:
        return ""
    text = text.replace("\n"," ").replace("\r"," ")
    text = text.replace('"','')
    return " ".join(text.split())[:300]

# ───────── LOAD CORPUS ─────────
def load_corpus():
    docs = []
    for md in DATA_DIR.rglob("*.md"):
        try:
            content = md.read_text(encoding="utf-8")
            company = md.parts[-2].lower()
            docs.append({"company":company, "content":content})
        except:
            pass
    return docs

# ───────── RETRIEVAL ─────────
def retrieve(docs, issue, company):
    scored = []
    for d in docs:
        score = 0
        if d["company"] == company.lower():
            score += 50
        if any(w in d["content"].lower() for w in issue.lower().split()):
            score += 5
        scored.append((score, d["content"]))

    scored.sort(reverse=True)
    return "\n".join([c[:400] for _, c in scored[:3]])

# ───────── PRODUCT AREA ─────────
def product_area(issue):
    t = issue.lower()
    if "login" in t or "account" in t:
        return "account_access"
    if "payment" in t or "refund" in t:
        return "billing"
    if "test" in t or "assessment" in t:
        return "assessment"
    if "error" in t or "bug" in t:
        return "platform_issue"
    if "fraud" in t or "card" in t or "scam" in t:
        return "fraud"
    return "general_support"

# ───────── FALLBACK ─────────
def fallback(issue):
    return f"Based on your issue: '{issue[:50]}...', please verify your account settings or system configuration. If the issue persists, contact support."
# ───────── GENERATE ─────────
def generate(client, corpus, issue):
    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role":"system","content":"Return only JSON"},
                {"role":"user","content": corpus + "\n\n" + issue}
            ],
            temperature=0
        )

        raw = res.choices[0].message.content

        if "{" in raw:
            raw = raw[raw.find("{"):raw.rfind("}")+1]
            data = json.loads(raw)
        else:
            raise Exception()

        return {
            "status": data.get("status","replied"),
            "response": clean(data.get("response","")),
            "justification": clean(data.get("justification","")),
            "request_type": data.get("request_type","product_issue")
        }

    except:
        return {
            "status":"replied",
            "response": fallback(issue),
            "justification":"Fallback used",
            "request_type":"product_issue"
        }

# ───────── VALIDATION (CRITICAL FIX) ─────────
def validate(result, issue):
    high_risk = ["fraud","stolen","unauthorized","scam","card","blocked"]

    if any(x in issue.lower() for x in high_risk):
        result["status"] = "escalated"
        result["response"] = "This appears to be a sensitive financial or security issue. We are escalating your request to a human support agent for secure handling."
        result["justification"] = "High-risk issue detected (fraud/card). As per support policy, escalated to human agent."

    return result

# ───────── MAIN ─────────
# clear old log
with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("AI Agent Execution Log\n\n")
def main():

    api_key = os.environ.get("GROQ_API_KEY","")
    if not api_key:
        print("❌ Set GROQ_API_KEY")
        return

    client = Groq(api_key=api_key)

    print("🚀 Loading corpus...")
    docs = load_corpus()
    print(f"✅ {len(docs)} documents loaded\n")

    with open(TICKETS_IN, encoding="utf-8") as f:
        tickets = list(csv.DictReader(f))

    results = []

    for i, t in enumerate(tickets,1):
        issue   = clean(t.get("Issue",""))
        subject = clean(t.get("Subject",""))
   
        company = clean(t.get("Company",""))

        print("="*60)
        print(f"🧾 Ticket {i}")
        print(f"Issue   : {issue[:100]}")
        print(f"Company : {company}")

        corpus = retrieve(docs, issue, company)

        result = generate(client, corpus, issue)
        result = validate(result, issue)

        area = product_area(issue)

        print(f"\n✅ Status        : {result['status']}")
        print(f"📂 Product Area : {area}")
        print(f"💬 Response     : {result['response'][:150]}")
        print(f"🧠 Justification: {result['justification']}")
        print("="*60)
       
        log_write("="*60)
        log_write(f"Ticket {i}")
        log_write(f"Issue: {issue}")
        log_write(f"Company: {company}")
        log_write(f"Status: {result['status']}")
        log_write(f"Product Area: {area}")
        log_write(f"Response: {result.get('response','N/A')}")
        log_write(f"Justification: {result.get('justification','N/A')}")
        log_write("="*60)



        results.append({
            "issue":issue,
            "subject":subject,
            "company":company,
            "status":result["status"],
            "product_area":area,
            "response":result["response"],
            "justification":result["justification"],
            "request_type":result["request_type"]
        })

        time.sleep(0.2)

    # ───────── SAVE CLEAN CSV ─────────
    with open(OUTPUT_CSV,"w",newline="",encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["issue","subject","company","status","product_area","response","justification","request_type"],
            quoting=csv.QUOTE_ALL
        )
        writer.writeheader()
        writer.writerows(results)

    print("\n🎉 DONE — CSV READY FOR SUBMISSION")

if __name__ == "__main__":
    main()