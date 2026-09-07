# B30 Controller — License Setup (GitHub + ZarinPal)

## 1. Generate keys (done)
- `private.pem` (KEEP SECRET) + `public.pem` generated via `generate_keys.py`
- `public.pem` is injected into `license_helper.py` → baked into `B30Controller.exe`
- `private.pem` goes to GitHub Secret `LICENSE_PRIVATE_PEM` (never commit)

## 2. Get ZarinPal MerchantID
- Register at https://www.zarinpal.com → get `MerchantID` (36 chars)
- Put it in GitHub repo → Settings → Secrets → `ZARINPAL_MERCHAN`T

## 3. GitHub repo setup
1. Create repo `B30-Controller`
2. Push `D:\Projects` as repo root:
   - `docs/` is GitHub Pages source (Settings → Pages → Source: `docs/` on `main` or `gh-pages`)
   - `.github/workflows/verify.yml` handles payment verification
3. Enable Pages: Settings → Pages → Branch `main` / folder `/docs` (or `gh-pages` branch)
4. Add Secrets:
   - `ZARINPAL_MERCHANT` = your MerchantID
   - `LICENSE_PRIVATE_PEM` = content of `D:\Projects\private.pem`
   - (Optional) `GH_PAT` if you want browser dispatch without 401 — but manual Issue fallback works without it

## 4. ZarinPal callback URL
- In ZarinPal panel set Callback URL to: `https://YOUR_USERNAME.github.io/B30-Controller/callback.html`
- Or use ZarinLink: set its redirect to same callback URL

## 5. Test flow
1. Run `B30Controller.exe` → activation dialog shows HWID
2. Click "باز کردن صفحه پرداخت" → browser opens `https://YOUR_USERNAME.github.io/B30-Controller/?hwid=...`
3. Pick plan → pay on ZarinPal
4. ZarinPal redirects to `callback.html?Authority=...&Status=OK`
5. Page fires `repository_dispatch` → Action verifies with ZarinPal → writes `licenses/HWID.lic` to `gh-pages` → page polls and shows download
6. User puts `license.lic` next to exe → restart → licensed

## 6. Fallback (no PAT / offline)
- If browser dispatch returns 401, user copies `Authority` into a new GitHub Issue
- You (or a second Action on `issues:opened`) trigger `workflow_dispatch` with same Authority/HWID → same verify → license issued

## 7. Build
```
build_secure.bat  → dist\B30Controller.exe (icon + obfuscation + license check)
```
`B30.ico` is embedded; `license_helper.py` is bundled.

## 8. Security notes
- `private.pem` never leaves Secrets; public key alone cannot forge licenses
- Amount is verified against plan (1500000/4500000/9000000 Rial) — mismatch fails
- HWID binding prevents sharing; expiry prevents forever use
- For offline sites: use manual `workflow_dispatch` — generate license.lic and deliver via USB

## 9. Replace placeholder
- In `docs/index.html` and `docs/callback.html` and `gui_controller_modern.py` replace `YOUR_GITHUB_USERNAME` / `YOUR_USERNAME` with your real GitHub username
