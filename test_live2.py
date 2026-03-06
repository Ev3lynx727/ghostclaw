import asyncio
from rich.console import Console
from rich.markdown import Markdown

async def main():
    content = []
    console = Console()
    import sys

    # Simulate stream
    for word in ["Hello ", "world!\n", "This ", "is ", "a ", "test.\n\n", "```python\nprint('hello')\n```"]:
        sys.stdout.write(word)
        sys.stdout.flush()
        content.append(word)
        await asyncio.sleep(0.5)

    full_text = "".join(content)

    # ANSI escape code logic to clear the raw stream
    lines_printed = full_text.count('\n') + 2
    # But this fails if text wraps or if we don't know exact lines.
    # A safer way without rich.Live is:
    sys.stdout.write(f"\033[{lines_printed}A\033[J")
    sys.stdout.flush()
    console.print(Markdown(full_text))

asyncio.run(main())
