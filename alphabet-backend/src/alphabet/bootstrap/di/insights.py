from dishka import Provider, Scope, provide_all

from alphabet.insights.application import ViewInsights


class InsightsDIProvider(Provider):
    interactors = provide_all(
        ViewInsights,
        scope=Scope.REQUEST,
    )
