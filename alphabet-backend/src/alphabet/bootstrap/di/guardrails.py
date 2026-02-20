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


class GuardrailsDIProvider(Provider):
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


class GuardrailWorkerDIProvider(Provider):
    interactors = provide_all(
        RegularCheck,
        scope=Scope.REQUEST,
    )
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
