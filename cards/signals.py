"""Django signals for broadcasting card changes to PyView clients."""

import asyncio
from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Card

# Import PyView's pub/sub hub directly
from pyview.live_socket import pub_sub_hub

CHANNEL = "cards_channel"

# Reference to the main event loop (set by app.py at startup)
_event_loop = None


def set_event_loop(loop):
    """Store reference to the main event loop for signal handlers."""
    global _event_loop
    _event_loop = loop
    print(f"[signals] Event loop set: {loop}")


def broadcast_change(action: str, card_id: int = None):
    """Broadcast a change to all connected PyView clients."""
    payload = {"action": action}
    if card_id is not None:
        payload["card_id"] = card_id

    if _event_loop is not None:
        asyncio.run_coroutine_threadsafe(
            pub_sub_hub.send_all_on_topic_async(CHANNEL, payload),
            _event_loop
        )
    else:
        print("[cards.signals] Warning: No event loop configured")


@receiver(post_save, sender=Card)
def on_card_save(sender, instance, created, **kwargs):
    """Handle card save - broadcast to all clients after transaction commits."""
    action = "card_created" if created else "state_changed"
    card_id = instance.id

    def do_broadcast():
        broadcast_change(action, card_id)

    # Delay broadcast until transaction commits so other connections can see the data
    transaction.on_commit(do_broadcast)


@receiver(post_delete, sender=Card)
def on_card_delete(sender, instance, **kwargs):
    """Handle card delete - broadcast to all clients after transaction commits."""
    card_id = instance.id

    def do_broadcast():
        broadcast_change("card_deleted", card_id)

    transaction.on_commit(do_broadcast)
