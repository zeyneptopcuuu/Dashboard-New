#!/usr/bin/env python3
"""
OLKA Sprint Dashboard - Jira'dan veri cekip index.html olusturur.

Gerekli ortam degiskenleri (GitHub Secrets uzerinden saglanir):
  JIRA_BASE_URL     -> ornek: https://olkaproduct.atlassian.net
  JIRA_EMAIL        -> Jira'ya API erisimi olan hesabin e-postasi
  JIRA_API_TOKEN    -> https://id.atlassian.com/manage-profile/security/api-tokens adresinden alinir
  JIRA_PROJECT_KEY  -> varsayilan: EWT (opsiyonel)

Kullanim:
  python scripts/generate_report.py
"""

import base64
import html
import os
import sys
import urllib.request
import urllib.error
import json
from datetime import datetime, timezone

# ----------------------------------------------------------------------------
# AYARLAR - marka eslesme kurallarini ve statu gruplarini burada duzenleyin
# ----------------------------------------------------------------------------

PROJECT_KEY = os.environ.get("JIRA_PROJECT_KEY", "EWT")
JIRA_BASE_URL = os.environ.get("JIRA_BASE_URL", "").rstrip("/")
JIRA_EMAIL = os.environ.get("JIRA_EMAIL", "")
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN", "")

ISSUETYPE_BRAND_MAP = {
    "Skechers": "Skechers",
    "Android": "Mobile",
    "iOS": "Mobile",
    "Klaud": "Klaud",
    "High5": "High5",
    "Brooks": "Brooks",
    "Hunter": "Hunter",
    "Steve Madden": "Steve Madden",
    "Asics": "Asics",
}

KEYWORD_BRAND_MAP = [
    ("klaud", "Klaud"),
    ("high5", "High5"),
    ("hunter", "Hunter"),
    ("brooks", "Brooks"),
    ("skechers", "Skechers"),
    ("skx", "Skechers"),
    ("steve madden", "Steve Madden"),
    ("asics", "Asics"),
    ("android", "Mobile"),
    (" ios", "Mobile"),
]

BRAND_ORDER = ["Skechers", "High5", "Mobile", "Klaud", "Steve Madden", "Brooks", "Hunter", "Asics"]
BRAND_LABEL = {
    "Skechers": "SKECHERS", "High5": "HIGH5", "Mobile": "MOBIL UYGULAMA (iOS & Android)",
    "Klaud": "KLAUD", "Steve Madden": "STEVE MADDEN", "Brooks": "BROOKS",
    "Hunter": "HUNTER", "Asics": "ASICS",
}

STATUS_BUCKET = {
    "Plan": "inprog", "To Do": "inprog", "Development": "inprog", "Review": "inprog", "UAT": "inprog",
    "Block": "risk", "Rejected": "risk",
    "Ready for Ship": "soon",
    "ONLIVE": "live", "Done": "live",
}

JQL = f"project = {PROJECT_KEY} AND sprint in openSprints() ORDER BY status ASC"

# ----------------------------------------------------------------------------
# JIRA'DAN VERI CEKME
# ----------------------------------------------------------------------------

def fetch_all_issues():
    if not (JIRA_BASE_URL and JIRA_EMAIL and JIRA_API_TOKEN):
        print("HATA: JIRA_BASE_URL / JIRA_EMAIL / JIRA_API_TOKEN ortam degiskenleri eksik.", file=sys.stderr)
        sys.exit(1)

    auth = base64.b64encode(f"{JIRA_EMAIL}:{JIRA_API_TOKEN}".encode()).decode()
    issues = []
    next_token = None
    while True:
        body = {
            "jql": JQL,
            "maxResults": 100,
            "fields": ["summary", "status", "issuetype"],
        }
        if next_token:
            body["nextPageToken"] = next_token
        req = urllib.request.Request(
            f"{JIRA_BASE_URL}/rest/api/3/search/jql",
            data=json.dumps(body).encode(),
            headers={
                "Authorization": f"Basic {auth}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            print(f"Jira API hatasi: {e.code} {e.read().decode()}", file=sys.stderr)
            sys.exit(1)

        issues.extend(data.get("issues", []))
        next_token = data.get("nextPageToken")
        if data.get("isLast", True) or not next_token:
            break
    return issues


def classify(issues):
    """key -> brand -> bucket -> [ {key, summary} ]"""
    result = {b: {"live": [], "soon": [], "inprog": [], "risk": []} for b in BRAND_ORDER}
    for it in issues:
        key = it["key"]
        f = it["fields"]
        itype = f["issuetype"]["name"]
        status = f["status"]["name"]
        summary = f["summary"].strip()

        brand = ISSUETYPE_BRAND_MAP.get(itype)
        if brand is None:
            low = summary.lower()
            for kw, b in KEYWORD_BRAND_MAP:
                if kw in low:
                    brand = b
                    break
        if brand not in BRAND_ORDER:
            continue

        bucket = STATUS_BUCKET.get(status)
        if
