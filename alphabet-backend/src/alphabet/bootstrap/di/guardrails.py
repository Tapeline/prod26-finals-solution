from dishka import Provider, Scope, provide, provide_all

from alphabet.guardrails.application.interactors import (
    ArchiveRule,
    CreateRule,
    ReadAuditForExperiment,
    ReadAuditForGuardRule,
    ReadRule,
    ReadRulesForExperiment,
    RegularCheck,
    UpdateRule,
)
from alphabet.guardrails.application.interfaces import (
    AuditLog,
    GuardRuleRepository,
)
from alphabet.guardrails.infrastructure.repos import (
    SqlAuditLog,
    SqlGuardRuleRepository,
)


class GuardrailsInteractorsDIProvider(Provider):
    interactors = provide_all(
        CreateRule,
        ReadRulesForExperiment,
        UpdateRule,
        ReadRule,
        ArchiveRule,
        ReadAuditForGuardRule,
        ReadAuditForExperiment,
        scope=Scope.REQUEST,
    )


class GuardrailWorkerDIProvider(Provider):
    interactors = provide_all(
        RegularCheck,
        scope=Scope.REQUEST,
    )


class GuardrailsStorageDIProvider(Provider):
    guard_repo = provide(
        SqlGuardRuleRepository,
        provides=GuardRuleRepository,
        scope=Scope.REQUEST,
    )
    audit_log = provide(
        SqlAuditLog,
        provides=AuditLog,
        scope=Scope.REQUEST,
    )


def get_guardrails_providers() -> list[Provider]:
    return [
        GuardrailsInteractorsDIProvider(),
        GuardrailsStorageDIProvider(),
        GuardrailWorkerDIProvider(),
    ]
