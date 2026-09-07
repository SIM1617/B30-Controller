# راهنمای گام‌به‌گام GitHub برای B30 Controller

> نام کاربری شما: **SIM1617** — ریپو: **B30-Controller**
> این راهنما را مرحله به مرحله انجام بده. هر جا گیر کردی عکس همان صفحه را بفرست.

---

## مرحله ۱ — ساخت ریپو روی GitHub (۲ دقیقه)

1. برو https://github.com/new
2. وارد شو با SIM1617 / er161720
3. تنظیمات ریپو:
   - **Repository name:** `B30-Controller` (دقیقا همین، با خط تیره)
   - **Description:** `B30 Traffic Controller - License via ZarinPal`
   - **Public** را انتخاب کن (برای GitHub Pages رایگان باید Public باشد)
   - **تیک Add a README file را نزن** (مهم — چون ما خودمان پوش می‌کنیم)
4. دکمه **Create repository** را بزن
5. صفحه‌ای می‌آید که می‌گوید *Quick setup* — همان را باز بگذار، سراغ مرحله ۲ برو

---

## مرحله ۲ — پوش کردن پروژه از همین کامپیوتر (من برایت اسکریپت ساختم)

من یک اسکریپت آماده کردم: `push_to_github.bat`

### روش A — اگر اسکریپت را اجرا کنی (ساده‌ترین):
1. در GitHub یک **Personal Access Token** بساز:
   - برو https://github.com/settings/tokens/new
   - Note: `B30 push`
   - Expiration: `90 days`
   - تیک‌ها: `repo` را کامل تیک بزن (همه زیرش)
   - **Generate token** → توکن را کپی کن (مثل `ghp_xxxx...` — یک بار نشان می‌دهد)
2. روی `push_to_github.bat` دوبار کلیک کن
3. توکن را Paste کن و Enter بزن — تمام!

### روش B — دستی (بدون اسکریپت):
PowerShell را باز کن و این دستورات را یکی یکی بزن:

```powershell
cd D:\Projects
git init
git add .
git commit -m "initial: B30 Controller with license + GitHub Pages"
git branch -M main
git remote add origin https://SIM1617:YOUR_TOKEN@github.com/SIM1617/B30-Controller.git
git push -u origin main
```

> به جای `YOUR_TOKEN` همان `ghp_xxxx` را بگذار.

---

## مرحله ۳ — فعال کردن GitHub Pages (۱ دقیقه)

1. برو به https://github.com/SIM1617/B30-Controller/settings/pages
2. در بخش **Build and deployment**:
   - **Source:** `Deploy from a branch`
   - **Branch:** `main` — پوشه: `/docs` را انتخاب کن
   - **Save** را بزن
3. بعد از ۱-۲ دقیقه، بالای همان صفحه لینک سایت می‌آید:
   - `https://SIM1617.github.io/B30-Controller/` ← صفحه خرید
   - `https://SIM1617.github.io/B30-Controller/callback.html` ← پیگیری پرداخت

> اگر Branch `main / docs` را نمی‌بینی، یعنی پوش هنوز انجام نشده — اول مرحله ۲ را کامل کن.

---

## مرحله ۴ — اضافه کردن Secrets (برای پرداخت زرین‌پال)

1. برو https://github.com/SIM1617/B30-Controller/settings/secrets/actions
2. دکمه **New repository secret** را بزن — دو بار:

### Secret اول:
- **Name:** `ZARINPAL_MERCHANT`
- **Value:** مرچنت کد زرین‌پال (۳۶ کاراکتر، از پنل زرین‌پال: https://next.zarinpal.com/merchant)

### Secret دوم:
- **Name:** `LICENSE_PRIVATE_PEM`
- **Value:** محتوای کامل فایل `D:\Projects\private.pem` را باز کن (با Notepad) و کل متن از `-----BEGIN RSA PRIVATE KEY-----` تا `-----END RSA PRIVATE KEY-----` را کپی و اینجا Paste کن

> این دو Secret برای Verify پرداخت و ساخت `license.lic` لازم است. بدون آنها پرداخت‌ها Verify نمی‌شود.

---

## مرحله ۵ — تنظیم زرین‌پال

### اگر زرین‌لینک داری:
1. برو https://next.zarinpal.com/zarinlink
2. یک زرین‌لینک جدید بساز برای هر پلن (یا یکی با مبلغ متغیر)
3. در `docs/index.html` خط `ZARIN_LINK_BASE = ""` را با آدرس زرین‌لینکت پر کن، مثلا:
   ```js
   const ZARIN_LINK_BASE = "https://zarinp.al/XXXXX";
   ```
4. دوباره `git add docs/index.html && git commit -m "set zarinlink" && git push`

### Callback URL در پنل زرین‌پال:
- در تنظیمات درگاه/زرین‌لینک، **Callback URL** را بگذار:
  ```
  https://SIM1617.github.io/B30-Controller/callback.html
  ```

---

## مرحله ۶ — تست کامل

1. `B30Controller.exe` را باز کن → دیالوگ فعال‌سازی با HWID می‌آید
2. ایمیل و پلن را انتخاب کن → **باز کردن صفحه پرداخت** → مرورگر باز می‌شود روی `https://SIM1617.github.io/B30-Controller/?hwid=...`
3. پرداخت را انجام بده (یا برای تست: از زرین‌لینک مستقیم پرداخت کن)
4. زرین‌پال به `callback.html?Authority=...&Status=OK` برمی‌گردد
5. دکمه **تایید پرداخت و ساخت لایسنس** را بزن
6. اگر 401 دیدی: دکمه **کپی متن برای Issue** را بزن → برو https://github.com/SIM1617/B30-Controller/issues/new → Paste و Submit → چند ثانیه بعد Action لایسنس را می‌سازد و لینک دانلود ظاهر می‌شود
7. `license.lic` را دانلود و کنار `B30Controller.exe` بگذار → برنامه را دوباره باز کن → بدون دیالوگ می‌آید ✓

---

## عیب‌یابی

| مشکل | دلیل | حل |
|------|------|-----|
| صفحه 404 می‌دهد | Pages فعال نیست یا Branch اشتباه | مرحله ۳ را دوباره چک کن — باید `main / docs` باشد |
| 401 در callback | طبیعی است (مرورگر PAT ندارد) | متن Issue را کپی و Issue بساز |
| Verify Failed | ZARINPAL_MERCHANT اشتباه | Secret را دوباره چک کن |
| license نامعتبر | HWID اشتباه یا private.pem ناهماهنگ | `public.pem` داخل `license_helper.py` باید از همین `private.pem` باشد (الان هست ✓) |

---

## فایل‌های آماده در D:\Projects

- `push_to_github.bat` — یک کلیک برای پوش
- `private.pem` / `public.pem` — کلیدها (private را هرگز کامیت نکن — در .gitignore هست)
- `.gitignore` — جلوی کامیت شدن private.pem و dist را می‌گیرد
