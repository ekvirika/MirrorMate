"""Base class every demo mode implements, plus the per-frame context."""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class FrameContext:
    """Everything a mode gets each frame."""
    frame: Any                    # BGR image (already mirrored) - draw on this
    w: int
    h: int
    now: float                    # time.time() this frame
    dt: float                     # seconds since last frame
    landmarks: Optional[Any]      # first detected hand (MediaPipe) or None
    gesture: Optional[str]        # 'rock' / 'paper' / 'scissors' / None
    robot: Any                    # shared RobotHand
    particles: Any                # shared fx.Particles
    flash: Any                    # shared fx.Flash


class Mode:
    """A self-contained demo. The app runs exactly one mode at a time."""

    name = "unnamed"       # shown in the menu and title bar
    icon = ""              # emoji for the menu (console only; cv2 can't render it)
    hint = ""              # one-line control hint shown at the bottom

    def on_enter(self, robot):
        """Called when the mode becomes active. Reset state here."""

    def on_exit(self, robot):
        """Called when leaving the mode. Stop animations here."""
        robot.cancel()

    def update(self, ctx: FrameContext):
        """Called every frame. Run logic and draw the mode's UI on ctx.frame."""

    def on_key(self, key, ctx: FrameContext):
        """Mode-specific keys (space, r, ...). Global keys are handled by the app."""

    def idle_ok(self):
        """True when the bored-robot fidgets may play (i.e. no game in progress)."""
        return True
