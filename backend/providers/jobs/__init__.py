from backend.config import settings
from backend.providers.jobs.arbeitnow import ArbeitnowProvider
from backend.providers.jobs.base import JobProvider


def get_job_providers() -> list[JobProvider]:
    """Arbeitnow needs no credentials, so it's always active. Adzuna is only
    added once its API keys are configured — adding a provider is purely
    additive here and never touches the matching engine (see the
    Extensibility NFR in docs/requirements.md).
    """
    providers: list[JobProvider] = [ArbeitnowProvider()]
    if settings.adzuna_app_id and settings.adzuna_app_key:
        from backend.providers.jobs.adzuna import AdzunaProvider

        providers.append(AdzunaProvider(settings.adzuna_app_id, settings.adzuna_app_key))
    return providers
