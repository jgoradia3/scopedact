from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Protocol

from .models import Permission


@dataclass(frozen=True)
class AuthorityRecord:
    principal: str
    permissions: frozenset[Permission]
    source: str
    issued_at: datetime
    expires_at: datetime
    key_id: str


class AuthoritySource(Protocol):
    def resolve(self, principal: str) -> AuthorityRecord: ...


def _canonical(body: dict) -> bytes:
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode()


def create_signed_bundle(*, principal: str, permissions: frozenset[Permission], secret: str, key_id: str="local:v1", lifetime_minutes: int=60, now: datetime|None=None) -> dict:
    if not secret: raise ValueError("authority signing secret must not be empty")
    if not 1 <= lifetime_minutes <= 1440: raise ValueError("lifetime must be 1 to 1440 minutes")
    issued=now or datetime.now(timezone.utc)
    body={"schema":"scopedact-authority/v1","principal":principal,"permissions":[p.to_dict() for p in sorted(permissions)],"issued_at":issued.isoformat(),"expires_at":(issued+timedelta(minutes=lifetime_minutes)).isoformat(),"key_id":key_id}
    return {**body,"signature":hmac.new(secret.encode(),_canonical(body),hashlib.sha256).hexdigest()}


class SignedBundleAuthoritySource:
    def __init__(self, path: str|Path, secret: str, *, now=None): self.path=Path(path); self.secret=secret; self.now=now
    def resolve(self, principal: str) -> AuthorityRecord:
        document=json.loads(self.path.read_text(encoding="utf-8")); expected={"schema","principal","permissions","issued_at","expires_at","key_id","signature"}
        if set(document)!=expected or document["schema"]!="scopedact-authority/v1": raise ValueError("invalid authority bundle schema")
        signature=document.pop("signature")
        digest=hmac.new(self.secret.encode(),_canonical(document),hashlib.sha256).hexdigest()
        if not self.secret or not hmac.compare_digest(signature,digest): raise ValueError("authority bundle signature is invalid")
        if document["principal"]!=principal: raise ValueError("authority bundle principal mismatch")
        issued=datetime.fromisoformat(document["issued_at"]); expires=datetime.fromisoformat(document["expires_at"]); current=self.now or datetime.now(timezone.utc)
        if issued.tzinfo is None or expires.tzinfo is None: raise ValueError("authority bundle timestamps must include timezone")
        if current < issued-timedelta(minutes=5): raise ValueError("authority bundle is not yet valid")
        if current >= expires: raise ValueError("authority bundle has expired")
        try: permissions=frozenset(Permission(x["action"],x["resource"]) for x in document["permissions"])
        except (KeyError,TypeError) as error: raise ValueError("invalid authority permissions") from error
        return AuthorityRecord(principal,permissions,"signed-local-bundle",issued,expires,document["key_id"])
