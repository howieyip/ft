import hashlib

m = hashlib.md5('031228QIAOlyoo'.encode(encoding='utf-8'))
print(m.hexdigest())
