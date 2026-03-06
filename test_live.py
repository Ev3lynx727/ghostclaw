import asyncio
from rich.live import Live
from rich.text import Text
from rich.markdown import Markdown
from rich.console import Console
import time

async def main():
    console = Console()
    content = []

    with Live(Text(""), console=console, refresh_per_second=10, transient=True) as live:
        for word in ["Hello ", "world!\n", "This ", "is ", "a ", "test.\n\n", "```python\nprint('hello')\n```"]:
            content.append(word)
            live.update(Text("".join(content)))
            await asyncio.sleep(0.5)

    console.print(Markdown("".join(content)))

asyncio.run(main())
