from call_llm.profile import Profile
from pyfiglet import figlet_format
from rich.panel import Panel
from rich.console import Console
from rich.align import Align
from rich.columns import Columns


def display_header(console: Console, profile: Profile):

    titre = figlet_format("Agent Smith", font="slant")
    stats = [
        Panel(f"Mode: {profile.mode}", style="bold"),
        Panel(f"Provider: {profile.provider_name}", style="bold"),
        Panel(f"Model: {profile.model_name}", style="bold"),
        ]
    console.print(
        Panel(
            Align.center(titre, style="blue"),
            border_style="blue"
        )
    )
    console.print(Columns(stats, expand=True))
