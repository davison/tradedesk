from tradedesk.events import DomainEvent, event


class BacktestConfig:
    pass

class BacktestSummary:
    pass

@event
class BacktestStartedEvent(DomainEvent):
    run_id: str
    config: BacktestConfig

@event
class BacktestFinishedEvent(DomainEvent):
    run_id: str
    summary: BacktestSummary
