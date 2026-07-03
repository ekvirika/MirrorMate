"""
IdleBuddy - the robot's personality when nobody is playing with it.

If no hand has been seen for a while (and the active mode says it's safe),
the hand plays a random fidget: drumming its fingers, stretching, or waving.
A little caption appears on screen so people notice.
"""

import random
import time

FIDGET_MIN_WAIT = 15.0
FIDGET_MAX_WAIT = 28.0
CAPTION_DURATION = 3.0

_FIDGETS = [
    ("drum",    "* drums fingers impatiently *"),
    ("stretch", "* stretches *"),
    ("wave",    "* waves at nobody *"),
    ("drum",    "* is getting bored... *"),
]


class IdleBuddy:
    def __init__(self):
        self.caption = ""
        self.caption_until = 0.0
        self._arm()

    def _arm(self):
        self.next_at = time.time() + random.uniform(FIDGET_MIN_WAIT, FIDGET_MAX_WAIT)

    def tick(self, ctx, mode):
        # Someone's here - stay professional, push the fidget back.
        if ctx.landmarks is not None:
            self._arm()
            return

        if ctx.now < self.next_at or not mode.idle_ok() or ctx.robot.busy():
            return

        action, caption = random.choice(_FIDGETS)
        getattr(ctx.robot, action)()
        self.caption = caption
        self.caption_until = ctx.now + CAPTION_DURATION
        self._arm()

    def active_caption(self, now):
        return self.caption if now < self.caption_until else None
