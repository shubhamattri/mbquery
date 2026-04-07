"""Configuration dataclasses for mbquery."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AuthConfig:
    method: str  # "api-key" or "session"
    api_key: str | None = None
    email: str | None = None
    password: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> AuthConfig:
        return cls(
            method=data["method"],
            api_key=data.get("api_key"),
            email=data.get("email"),
            password=data.get("password"),
        )

    def to_dict(self) -> dict:
        d: dict = {"method": self.method}
        if self.method == "api-key":
            d["api_key"] = self.api_key
        elif self.method == "session":
            d["email"] = self.email
            d["password"] = self.password
        return d


@dataclass
class Profile:
    name: str
    url: str
    auth: AuthConfig
    default_db: int | None = None

    @classmethod
    def from_dict(cls, name: str, data: dict) -> Profile:
        return cls(
            name=name,
            url=data["url"],
            auth=AuthConfig.from_dict(data["auth"]),
            default_db=data.get("default_db"),
        )

    def to_dict(self) -> dict:
        d: dict = {"url": self.url, "auth": self.auth.to_dict()}
        if self.default_db is not None:
            d["default_db"] = self.default_db
        return d


@dataclass
class LLMConfig:
    provider: str
    model: str
    api_key: str | None = None
    base_url: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> LLMConfig:
        return cls(
            provider=data["provider"],
            model=data["model"],
            api_key=data.get("api_key"),
            base_url=data.get("base_url"),
        )

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "api_key": self.api_key,
            "base_url": self.base_url,
        }


@dataclass
class Defaults:
    format: str = "table"
    limit: int = 100
    redact_pii: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> Defaults:
        return cls(
            format=data.get("format", "table"),
            limit=data.get("limit", 100),
            redact_pii=data.get("redact_pii", True),
        )

    def to_dict(self) -> dict:
        return {"format": self.format, "limit": self.limit, "redact_pii": self.redact_pii}


@dataclass
class AppConfig:
    active_profile: str | None = None
    profiles: dict[str, Profile] = field(default_factory=dict)
    llm: LLMConfig | None = None
    defaults: Defaults = field(default_factory=Defaults)

    @classmethod
    def empty(cls) -> AppConfig:
        return cls()

    @classmethod
    def from_dict(cls, data: dict) -> AppConfig:
        profiles = {}
        for name, pdata in data.get("profiles", {}).items():
            profiles[name] = Profile.from_dict(name, pdata)

        llm = None
        if data.get("llm"):
            llm = LLMConfig.from_dict(data["llm"])

        defaults = Defaults.from_dict(data.get("defaults", {}))

        return cls(
            active_profile=data.get("active_profile"),
            profiles=profiles,
            llm=llm,
            defaults=defaults,
        )

    def to_dict(self) -> dict:
        return {
            "active_profile": self.active_profile,
            "profiles": {name: p.to_dict() for name, p in self.profiles.items()},
            "llm": self.llm.to_dict() if self.llm else None,
            "defaults": self.defaults.to_dict(),
        }
