"""Django signals for broadcasting model changes to PyView clients."""

import asyncio
from typing import Type

from django.db import models, transaction
from django.db.models.signals import post_save, post_delete

from pyview.live_socket import pub_sub_hub

from .mixin import AliveMixin
from .store import get_store

# Reference to the main event loop (set by setup_alive)
_event_loop = None


def set_event_loop(loop):
    """Store reference to the main event loop for signal handlers."""
    global _event_loop
    _event_loop = loop


def broadcast_change(channel: str, action: str, item_id: int = None):
    """Broadcast a change to all connected PyView clients."""
    payload = {"action": action}
    if item_id is not None:
        payload["item_id"] = item_id

    if _event_loop is not None:
        future = asyncio.run_coroutine_threadsafe(
            pub_sub_hub.send_all_on_topic_async(channel, payload),
            _event_loop
        )
        # Optional: add error handling callback
        def on_done(f):
            try:
                f.result()
            except Exception as e:
                print(f"[alive.signals] Broadcast error: {e}")
        future.add_done_callback(on_done)
    else:
        print("[alive.signals] Warning: No event loop configured")


def _make_save_handler(model: Type[models.Model]):
    """Create a post_save handler for a model."""
    store = get_store(model)
    channel = store.channel

    def on_save(sender, instance, created, **kwargs):
        action = "item_created" if created else "state_changed"
        item_id = instance.pk

        def do_broadcast():
            broadcast_change(channel, action, item_id)

        transaction.on_commit(do_broadcast)

    return on_save


def _make_delete_handler(model: Type[models.Model]):
    """Create a post_delete handler for a model."""
    store = get_store(model)
    channel = store.channel

    def on_delete(sender, instance, **kwargs):
        item_id = instance.pk

        def do_broadcast():
            broadcast_change(channel, "item_deleted", item_id)

        transaction.on_commit(do_broadcast)

    return on_delete


def setup_signals():
    """
    Register signal handlers for all models with AliveMixin.

    Call this after Django setup and after setting the event loop.
    """
    from django.apps import apps

    for model in apps.get_models():
        if issubclass(model, AliveMixin):
            # Create and connect handlers
            save_handler = _make_save_handler(model)
            delete_handler = _make_delete_handler(model)

            post_save.connect(save_handler, sender=model)
            post_delete.connect(delete_handler, sender=model)

            print(f"[alive.signals] Registered signals for {model._meta.label}")
