from tradedesk.events import DomainEvent, event


class Position:
    pass

@event
class PositionUpdatedEvent(DomainEvent):
    instrument: str
    position: Position

@event
class PortfolioValuedEvent(DomainEvent):
    equity: float
    cash: float
