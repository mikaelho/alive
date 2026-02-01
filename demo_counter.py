#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "pyview-web",
#   "uvicorn",
# ]
# ///

from typing import TypedDict
from pyview import LiveView, playground
from pyview.template.template_view import TemplateView
from pyview.events import AutoEventDispatch, event
from string.templatelib import Template
import uvicorn


class CountContext(TypedDict):
    count1: int
    count2: int


class CounterView(AutoEventDispatch, TemplateView, LiveView[CountContext]):
    async def mount(self, socket, session):
        socket.context = {"count1": 0, "count2": 0}

    @event
    async def increment(self, event, payload, socket):
        socket.context["count"] += 1

    @event
    async def decrement(self, event, payload, socket):
        socket.context["count"] -= 1

    def button(self, ref, text, color: str = "blue") -> Template:
        return t"""
        <button phx-click={ref}
                class="bg-{color}-500 px-4 py-2 text-white rounded">{text}</button>
        """

    def template(self, assigns: CountContext, meta) -> Template:
        return t"""
        <div class="flex items-center justify-center min-h-screen">
            <div class="flex flex-col items-center gap-4">
                <h1 class="text-2xl">Counter: {assigns['count']}</h1>
                <div class="flex gap-2">
                    {self.button(self.decrement, "-", "red")}
                    {self.button(self.increment, "+", "blue")}
                </div>
            </div>
        </div>
        """

app = (
    playground()
    .with_live_view(CounterView)
    .with_title("Counter")
    .with_css('<script src="https://cdn.tailwindcss.com"></script>')
    .build()
)

if __name__ == "__main__":
    uvicorn.run("demo_counter:app", host="0.0.0.0", port=8000, reload=True)
