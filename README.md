# OLKA Sprint Dashboard

Jira'daki aktif sprint verisinden otomatik uretilen, marka bazli sprint durum raporu.
GitHub Actions ile **her Pazartesi** otomatik guncellenir ve GitHub Pages uzerinden yayinlanir.

## Kurulum (tek seferlik)

### 1) Bu repoyu GitHub'a yukleyin
Bu klasordeki tum dosyalari (README, index.html, scripts/, .github/) mevcut reponuza
yukleyin (veya bu klasoru oldugu gibi yeni bir repo olarak push edin).

### 2) Jira API Token olusturun
1. https://id.atlassian.com/manage-profile/security/api-tokens adresine gidin
2. "Create API token" ile yeni bir token olusturun, kopyalayin
3. Bu token'i olusturan hesabin, `EWT` projesindeki sprintleri gorme yetkisi olmali

### 3) GitHub Secrets ekleyin
Repo -> **Settings -> Secrets and variables -> Actions -> New repository secret**
asagidaki 3 secret'i ekleyin:

| Secret adi | Deger |
|---|---|
| `JIRA_BASE_URL` | `https://olkaproduct.atlassian.net` |
| `JIRA_EMAIL` | Jira hesabinizin e-postasi |
| `JIRA_API_TOKEN` | 2. adimda olusturdugunuz token |

(Opsiyonel) Farkli bir proje icin `JIRA_PROJECT_KEY` secret'i da ekleyebilirsiniz; eklenmezse
varsayilan olarak `EWT` kullanilir.

### 4) GitHub Pages'i acin
Repo -> **Settings -> Pages**
- Source: **Deploy from a branch**
- Branch: `main` (veya kullandiginiz ana dal) / **root**
- Kaydedin. Birkaç dakika icinde siteniz `https://<kullanici-adiniz>.github.io/<repo-adi>/`
  adresinde yayinda olacak.

### 5) Ilk calistirmayi manuel tetikleyin (opsiyonel)
Repo -> **Actions -> Sprint Dashboard - Haftalik Guncelleme -> Run workflow**
Bu, `index.html` dosyasini hemen Jira'daki guncel veriyle yeniden uretip commit'ler.

## Nasil calisir?

- `scripts/generate_report.py`: Jira REST API'ye baglanir (`project = EWT AND sprint in
  openSprints()`), isleri marka ve statuye gore siniflandirir, `index.html` dosyasini uretir.
- `.github/workflows/weekly-update.yml`: Her Pazartesi 06:00 UTC'de bu scripti calistirir,
  degisiklik varsa otomatik commit + push eder. GitHub Pages de dosya degistiginde otomatik
  yeniden yayinlar.
- Istediginiz zaman **Actions** sekmesinden "Run workflow" ile elle de tetikleyebilirsiniz.

## Ozellestirme

- **Marka eslesmesi**: `scripts/generate_report.py` icindeki `ISSUETYPE_BRAND_MAP` ve
  `KEYWORD_BRAND_MAP` sozlukleri, hangi Jira issue type / anahtar kelimenin hangi markaya
  denk geldigini belirler. Yeni bir marka eklenirse buraya satir eklemeniz yeterli.
- **Statu gruplari**: `STATUS_BUCKET` sozlugu hangi Jira statusunun "canlida / yakinda /
  suruyor / dikkat gerekli" kategorisine girdigini belirler.
- **Zamanlama**: `.github/workflows/weekly-update.yml` icindeki `cron` degerini
  degistirerek farkli bir gun/saat secebilirsiniz (cron format: dakika saat gun ay haftagunu,
  UTC saat dilimindedir).
- **Marka bagimsiz / genel isler**: Belirli bir markaya eslenemeyen isler (ornegin PIM
  altyapisi, tum markalari ilgilendiren testler) rapora dahil edilmez. Bunlarin da
  gosterilmesini isterseniz `BRAND_ORDER` listesine `"Genel"` ekleyip `KEYWORD_BRAND_MAP`'in
  sonuna bir fallback kurali eklemeniz yeterli.

## Not

Bu rapordaki metinler (ozet cumleler, "oncelikli konular" gibi yorum iceren bolumler)
onceki elle hazirlanan versiyonda Jira yorumlarindan/aciklamalarindan cikarilan is
bilgisiyle zenginlestirilmisti. Otomatik surumde bu yorumlar yapilamadigi icin her
markanin altinda ilgili is basliklari dogrudan Jira'dan cekilip listelenir (tiklaninca
ilgili Jira kaydina gider). Ozel bir haftada daha detayli/yorumlu bir ozet gerekiyorsa,
bu sohbette tekrar talep edebilirsiniz.
