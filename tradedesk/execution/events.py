from tradedesk.events import DomainEvent, event


class Order:
    pass


class Fill:
    pass


@event
class OrderSubmittedEvent(DomainEvent):
    strategy_id: str
    order: Order


@event
class OrderFilledEvent(DomainEvent):
    order_id: str
    fill: Fill


@event
class OrderRejectedEvent(DomainEvent):
    order_id: str
    reason: str
