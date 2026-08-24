"""
Tests for Event Bus
"""

import pytest

from src.core.events import Event, get_event_bus


@pytest.mark.asyncio
async def test_event_bus_publish_subscribe():
    """Test basic event publishing and subscription"""
    event_bus = get_event_bus()
    received_events = []

    def handler(event: Event):
        received_events.append(event)

    event_bus.subscribe("test.event", handler)

    event = Event(name="test.event", data={"key": "value"})
    event_bus.publish(event)

    assert len(received_events) == 1
    assert received_events[0].name == "test.event"
    assert received_events[0].data["key"] == "value"


@pytest.mark.asyncio
async def test_event_bus_async_handler():
    """Test async event handler"""
    event_bus = get_event_bus()
    received_events = []

    async def async_handler(event: Event):
        received_events.append(event)

    event_bus.subscribe_async("test.async", async_handler)

    event = Event(name="test.async", data={"test": "data"})
    await event_bus.publish_async(event)

    assert len(received_events) == 1
    assert received_events[0].name == "test.async"


@pytest.mark.asyncio
async def test_event_bus_multiple_subscribers():
    """Test multiple subscribers to same event"""
    event_bus = get_event_bus()
    handler1_called = []
    handler2_called = []

    def handler1(event: Event):
        handler1_called.append(True)

    def handler2(event: Event):
        handler2_called.append(True)

    event_bus.subscribe("multi.event", handler1)
    event_bus.subscribe("multi.event", handler2)

    event = Event(name="multi.event", data={})
    event_bus.publish(event)

    assert len(handler1_called) == 1
    assert len(handler2_called) == 1


@pytest.mark.asyncio
async def test_event_bus_unsubscribe():
    """Test unsubscribing from events"""
    event_bus = get_event_bus()
    received_events = []

    def handler(event: Event):
        received_events.append(event)

    event_bus.subscribe("unsub.event", handler)
    event_bus.unsubscribe("unsub.event", handler)

    event = Event(name="unsub.event", data={})
    event_bus.publish(event)

    assert len(received_events) == 0
