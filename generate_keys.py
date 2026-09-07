from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
priv = k.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.TraditionalOpenSSL,
    encryption_algorithm=serialization.NoEncryption()
)
pub = k.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)

with open("D:/Projects/private.pem", "wb") as f:
    f.write(priv)
with open("D:/Projects/public.pem", "wb") as f:
    f.write(pub)
print("Keys generated:", len(priv), len(pub))