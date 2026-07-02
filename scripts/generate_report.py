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
        if bucket is None:
            continue
        result[brand][bucket].append({"key": key, "summary": summary})
    return result


# ----------------------------------------------------------------------------
# HTML URETIMI (kurumsal sablon)
# ----------------------------------------------------------------------------

NAVY, GOLD, INK, SLATE, LINE, PAPER, CARD = (
    "#132339", "#A6813C", "#1F2933", "#5B6774", "#DCE1E7", "#EFEFEC", "#FFFFFF",
)
GREEN, BLUE, RED = "#1F6F4B", "#2E5C8A", "#8A2E22"
SERIF = "Georgia, 'Times New Roman', serif"
SANS = "'Segoe UI', Arial, Helvetica, sans-serif"


def jlink(key, text):
    href = f"{JIRA_BASE_URL}/browse/{key}"
    return f'<a href="{href}" style="color:{SLATE}; text-decoration:underline;">{html.escape(text)}</a>'


def bullet_rows(items, color):
    if not items:
        return ""
    rows = "".join(
        f'<tr><td width="16" valign="top" style="padding:3px 4px 3px 0; font-size:13px; color:{color}; '
        f'font-family:{SANS}; line-height:1.55;">&#8226;</td>'
        f'<td style="padding:3px 0; font-size:12px; color:{INK}; line-height:1.55; font-family:{SANS};">{jlink(it["key"], it["summary"])}</td></tr>'
        for it in items
    )
    return f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:6px 0 4px 0;">{rows}</table>'


def metric_row(counts):
    def cell(num, label, color, last=False):
        border = "" if last else f"border-right:1px solid {LINE};"
        return (f'<td width="25%" align="center" style="padding:10px 4px; {border}">'
                f'<div style="font-family:{SERIF}; font-size:22px; color:{color}; line-height:1;">{num}</div>'
                f'<div style="font-family:{SANS}; font-size:9px; color:{SLATE}; text-transform:uppercase; '
                f'letter-spacing:0.3px; margin-top:4px;">{label}</div></td>')
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
            f'style="margin:12px 0; background-color:#FAFAF9; border:1px solid {LINE};"><tr>'
            + cell(counts["live"], "Canlida", GREEN)
            + cell(counts["soon"], "Yakinda", BLUE)
            + cell(counts["inprog"], "Suruyor", SLATE)
            + cell(counts["risk"], "Dikkat", RED if counts["risk"] > 0 else SLATE, last=True)
            + '</tr></table>')


def severity_color(counts):
    total = sum(counts.values()) or 1
    ratio = counts["risk"] / total
    if counts["risk"] >= 3 or ratio > 0.4:
        return RED
    if counts["risk"] > 0:
        return GOLD
    return "#C7CDD3"


def build_brand_card(brand, data):
    counts = {k: len(v) for k, v in data.items()}
    total = sum(counts.values())
    if total == 0:
        return ""
    sev = severity_color(counts)
    card = (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
            f'style="margin-bottom:18px; background-color:{CARD}; border:1px solid {LINE}; border-left:4px solid {sev};">'
            f'<tr><td style="padding:18px 20px;">'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
            f'<td><div style="font-family:{SERIF}; font-size:16px; color:{NAVY}; font-weight:700;">{BRAND_LABEL[brand]}</div></td>'
            f'<td align="right" valign="top"><span style="font-family:{SANS}; font-size:10px; color:{SLATE}; '
            f'text-transform:uppercase; letter-spacing:0.4px;">{total} Is Kalemi</span></td>'
            f'</tr></table>')
    card += metric_row(counts)
    if data["live"]:
        card += f'<div style="font-family:{SANS}; font-size:10px; font-weight:700; letter-spacing:0.4px; color:{GREEN}; text-transform:uppercase; margin-top:10px;">Tamamlanan / Canliya Alinan</div>'
        card += bullet_rows(data["live"], GREEN)
    if data["soon"]:
        card += f'<div style="font-family:{SANS}; font-size:10px; font-weight:700; letter-spacing:0.4px; color:{BLUE}; text-transform:uppercase; margin-top:10px;">Yakinda Canlida</div>'
        card += bullet_rows(data["soon"], BLUE)
    if data["risk"]:
        card += f'<div style="font-family:{SANS}; font-size:10px; font-weight:700; letter-spacing:0.4px; color:{RED}; text-transform:uppercase; margin-top:10px;">Dikkat Gerekli</div>'
        card += bullet_rows(data["risk"], RED)
    if data["inprog"]:
        card += (f'<div style="font-family:{SANS}; font-size:10px; font-weight:700; letter-spacing:0.4px; color:{SLATE}; '
                  f'text-transform:uppercase; margin-top:14px; margin-bottom:4px; border-top:1px solid {LINE}; padding-top:10px;">'
                  f'Mevcut Sprintte Tamamlanamayan &middot; {len(data["inprog"])} is</div>'
                  f'<div style="font-family:{SANS}; font-size:10.5px; color:#8A94A0; font-style:italic; margin-bottom:6px;">'
                  f'Mevcut sprint kapsaminda tamamlanamadigi icin bir sonraki sprinte aktarilmistir. '
                  f'Maddelere tiklayarak ilgili Jira kaydina ulasabilirsiniz.</div>')
        card += bullet_rows(data["inprog"], SLATE)
    card += '</td></tr></table>'
    return card


def build_html(by_brand):
    totals = {"live": 0, "soon": 0, "inprog": 0, "risk": 0}
    for brand in BRAND_ORDER:
        for bucket in totals:
            totals[bucket] += len(by_brand[brand][bucket])
    grand_total = sum(totals.values())

    cards = "".join(build_brand_card(b, by_brand[b]) for b in BRAND_ORDER)
    now = datetime.now(timezone.utc).astimezone().strftime("%d.%m.%Y %H:%M")
    board_url = f"{JIRA_BASE_URL}/jira/software/projects/{PROJECT_KEY}/boards/1"

    return f'''<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OLKA Sprint Dashboard</title>
<style>
  body {{ margin:0; padding:0; background-color:{PAPER}; font-family:{SANS}; color:{INK}; }}
  table {{ border-collapse:collapse; }}
  a {{ color:{GOLD}; }}
</style>
</head>
<body>
<center>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:{PAPER};">
<tr><td align="center" style="padding:32px 12px;">
<table role="presentation" width="760" cellpadding="0" cellspacing="0" border="0" style="width:760px; max-width:760px; background-color:{CARD};">

  <tr><td style="padding:0;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:{NAVY};">
      <tr><td style="padding:34px 36px 26px 36px;">
        <div style="font-family:{SANS}; font-size:10px; font-weight:700; letter-spacing:2px; color:{GOLD}; text-transform:uppercase;">OLKA</div>
        <div style="font-family:{SERIF}; font-size:26px; color:#FFFFFF; margin-top:10px; line-height:1.25;">Sprint Durum Raporu</div>
        <div style="font-family:{SANS}; font-size:12px; color:#B9C2CC; margin-top:8px;">Otomatik olusturuldu: {now}</div>
        <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin-top:18px;"><tr>
          <td style="background-color:{GOLD}; padding:10px 20px;" align="center">
            <a href="{board_url}" style="font-family:{SANS}; font-size:11.5px; font-weight:700; color:{NAVY}; text-decoration:none; letter-spacing:0.2px;">JIRA SPRINT BOARD'U AC &nbsp;&#8594;</a>
          </td></tr></table>
      </td></tr>
      <tr><td style="height:3px; background-color:{GOLD};"></td></tr>
    </table>
  </td></tr>

  <tr><td style="padding:28px 36px 24px 36px;">
    <div style="font-family:{SANS}; font-size:10px; font-weight:700; letter-spacing:1.5px; color:{SLATE}; text-transform:uppercase; margin-bottom:4px;">Genel Durum</div>
    <div style="font-family:{SERIF}; font-size:15px; color:{INK}; line-height:1.5; margin-bottom:16px;">
      Bu donemde markalarimiz icin toplam <b>{grand_total} is kalemi</b> yurutuluyor.
    </div>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-top:1px solid {LINE}; border-bottom:1px solid {LINE};">
      <tr>
        <td width="25%" align="center" style="padding:18px 6px; border-right:1px solid {LINE};">
          <div style="font-family:{SERIF}; font-size:32px; color:{GREEN};">{totals['live']}</div>
          <div style="font-family:{SANS}; font-size:9.5px; color:{SLATE}; text-transform:uppercase; letter-spacing:0.4px; margin-top:6px;">Canlida /<br>Tamamlandi</div>
        </td>
        <td width="25%" align="center" style="padding:18px 6px; border-right:1px solid {LINE};">
          <div style="font-family:{SERIF}; font-size:32px; color:{BLUE};">{totals['soon']}</div>
          <div style="font-family:{SANS}; font-size:9.5px; color:{SLATE}; text-transform:uppercase; letter-spacing:0.4px; margin-top:6px;">Yakinda<br>Canlida</div>
        </td>
        <td width="25%" align="center" style="padding:18px 6px; border-right:1px solid {LINE};">
          <div style="font-family:{SERIF}; font-size:32px; color:{SLATE};">{totals['inprog']}</div>
          <div style="font-family:{SANS}; font-size:9.5px; color:{SLATE}; text-transform:uppercase; letter-spacing:0.4px; margin-top:6px;">Gelistirme /<br>Test Suruyor</div>
        </td>
        <td width="25%" align="center" style="padding:18px 6px;">
          <div style="font-family:{SERIF}; font-size:32px; color:{RED};">{totals['risk']}</div>
          <div style="font-family:{SANS}; font-size:9.5px; color:{SLATE}; text-transform:uppercase; letter-spacing:0.4px; margin-top:6px;">Dikkat<br>Gerekli</div>
        </td>
      </tr>
    </table>
  </td></tr>

  <tr><td style="padding:8px 36px 8px 36px;">
    <div style="font-family:{SANS}; font-size:10px; font-weight:700; letter-spacing:1.5px; color:{SLATE}; text-transform:uppercase; margin-bottom:2px;">Marka Bazli Durum</div>
    <div style="font-family:{SERIF}; font-size:15px; color:{INK}; margin-bottom:18px;">Her marka icin tamamlanan, yakinda canliya alinacak ve dikkat gerektiren isler</div>
    {cards}
  </td></tr>

  <tr><td style="padding:18px 36px 26px 36px; border-top:1px solid {LINE};">
    <div style="font-family:{SANS}; font-size:10.5px; color:#9AA6B2;">
      Bu sayfa GitHub Actions ile Jira'dan otomatik olarak haftalik guncellenir.<br>
      Son guncelleme: <b style="color:{SLATE};">{now}</b> &nbsp;|&nbsp; {PROJECT_KEY} Projesi
    </div>
  </td></tr>

</table>
</td></tr>
</table>
</center>
</body>
</html>
'''


def main():
    issues = fetch_all_issues()
    by_brand = classify(issues)
    out = build_html(by_brand)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(out)
    print(f"index.html olusturuldu ({len(issues)} is islendi).")


if __name__ == "__main__":
    main()
