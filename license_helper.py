import pathlib
import json
import base64
import hashlib
import uuid as _uuid
import datetime as _dt
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

LICENSE_FILE = "license.lic"

# This PEM is baked into the app at build time — generated from private.pem
PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAwvE6Mlh6X8ev3xt4zD/V
oycXDmJ5HjhqYJMzosj1+GVzjSDNqT10MgFJht7CCyg8I+9BdfupZn4GFjRyXDgb
WGw/DGnsD86osyESMo+SnDEVa0E8Epi+FWXKq2+ulks452nwv+yi6Aa4nYhInsRI
m4uhQc+QmkMmoUJbRPOFnRMpyktX4kFHK8Hu7HgTkl6AZ+7Z4clQ5cZbo+illfZz
JimzwrDiHoEcgFQLwwi4z5Ld3R5CNyQF93e2CJ7aEqr2hYg7kMgblozLqEQbCGad
UaViOf53EnpVlIizqwARCe4XIM7Kxvy9T0WSB+lLzdSv0WhK05XYkCEduuz0gLcg
WQIDAQAB
-----END PUBLIC KEY-----"""


def get_hwid() -> str:
    raw = f"{_uuid.getnode()}-{pathlib.Path.home()}"
    h = hashlib.sha256(str(raw).encode()).hexdigest()
    return f"{h[:4]}-{h[4:8]}-{h[8:12]}".upper()


# Back-compat alias
class HWID:
    @staticmethod
    def get() -> str:
        return get_hwid()

    @staticmethod
    def get_hwid() -> str:
        return get_hwid()


def _load_public_key():
    pem = PUBLIC_KEY_PEM.encode()
    if b"REPLACE_ME" in pem:
        return None
    try:
        return serialization.load_pem_public_key(pem)
    except Exception:
        return None


def verify_license_lic(path: pathlib.Path):
    try:
        p = pathlib.Path(path)
        if not p.exists():
            return False, "فایل license.lic یافت نشد"
        data = json.loads(p.read_text(encoding="utf-8"))
        payload = data.get("payload")
        sig_b64 = data.get("sig")
        if not payload or not sig_b64:
            return False, "فرمت لایسنس نامعتبر"
        pub = _load_public_key()
        if pub is None:
            # No embedded key yet (dev mode) — accept any non-empty license for testing
            # In production the key is injected by generate_keys.py
            try:
                pl = json.loads(payload)
                exp = pl.get("exp", "2099-12-31")
                if exp < _dt.date.today().isoformat():
                    return False, f"لایسنس منقضی شده: {exp}"
                return True, f"لایسنس تستی معتبر تا {exp}"
            except Exception as e:
                return False, str(e)
        sig = base64.b64decode(sig_b64.encode())
        pub.verify(sig, payload.encode(), padding.PKCS1v15(), hashes.SHA256())
        pl = json.loads(payload)
        hwid = pl.get("hwid", "")
        exp = pl.get("exp", "2099-12-31")
        if hwid and hwid != get_hwid():
            return False, f"لایسنس برای دستگاه دیگری است ({hwid})"
        if exp < _dt.date.today().isoformat():
            return False, f"لایسنس منقضی شده: {exp}"
        return True, f"پلن {pl.get('plan','-')} تا {exp}"
    except Exception as e:
        return False, str(e)


def create_license_payload(hwid: str, plan: str, exp: str) -> str:
    return json.dumps({"hwid": hwid, "plan": plan, "exp": exp}, sort_keys=True, ensure_ascii=False)


def sign_payload(payload: str, private_pem_path: str = "private.pem") -> str:
    priv = serialization.load_pem_private_key(
        pathlib.Path(private_pem_path).read_bytes(), password=None
    )
    sig = priv.sign(payload.encode(), padding.PKCS1v15(), hashes.SHA256())
    return base64.b64encode(sig).decode()


def issue_license_file(hwid: str, plan: str, exp: str, dest: str = "license.lic", private_pem_path: str = "private.pem"):
    payload = create_license_payload(hwid, plan, exp)
    sig = sign_payload(payload, private_pem_path)
    data = {"payload": payload, "sig": sig}
    pathlib.Path(dest).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return dest

