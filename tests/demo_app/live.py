"""Cumulative live view, owned by the SDK event loop; never queues RF reports.

Slow browsers skip intermediate *paint states*, not received counts. Each
browser has its own cursor and reconnects with an authoritative reset.
"""

import asyncio


class LiveView:
    def __init__(self, capacity=1000, interval=1 / 30):
        self.capacity, self.interval = capacity, interval
        self.generation, self.revision = 0, 0
        self.rows = {}
        self.changed = asyncio.Event()

    def notify(self):
        event, self.changed = self.changed, asyncio.Event()
        event.set()

    def reset(self):
        self.generation += 1
        self.revision = 0
        self.rows.clear()
        self.notify()

    def update(self, key, row):
        self.revision += 1
        if key in self.rows or len(self.rows) < self.capacity:
            self.rows[key] = (self.revision, row)
        self.notify()

    async def next(self, cursor=None):
        if cursor == (self.generation, self.revision):
            try:
                await asyncio.wait_for(self.changed.wait(), timeout=1)
            except TimeoutError:
                pass  # Idle heartbeat also detects a disconnected browser.
        reset = cursor is None or cursor[0] != self.generation
        if not reset and cursor[1] != self.revision:
            await asyncio.sleep(self.interval)
            reset = cursor[0] != self.generation  # Clear can happen during coalescing.
        after = -1 if reset else cursor[1]
        return {
            "cursor": (self.generation, self.revision),
            "reset": reset,
            "rows": [row for revision, row in self.rows.values() if revision > after],
            "view_capacity": self.capacity,
        }
