import json

class ContextBuilder:
    """Builds the context prompt for the AI engine."""

    def build_prompt(self, metrics: dict, issues: list, ghosts: list, flags: list, coupling_metrics: dict, import_edges: list) -> str:
        """
        Formats analysis data into an XML-tagged prompt for LLMs.
        """
        prompt = "Analyze the following codebase architecture and provide a 'Vibe Synthesis' report. "
        prompt += "Focus on system-level flow, cohesion, and tech stack best practices.\n\n"

        prompt += "<metrics>\n"
        prompt += json.dumps(metrics, indent=2) + "\n"
        prompt += "</metrics>\n\n"

        if issues:
            prompt += "<issues>\n"
            for issue in issues:
                prompt += f"- {issue}\n"
            prompt += "</issues>\n\n"

        if ghosts:
            prompt += "<ghosts>\n"
            for ghost in ghosts:
                prompt += f"- {ghost}\n"
            prompt += "</ghosts>\n\n"

        if flags:
            prompt += "<flags>\n"
            for flag in flags:
                prompt += f"- {flag}\n"
            prompt += "</flags>\n\n"

        if coupling_metrics:
            prompt += "<coupling_metrics>\n"
            prompt += json.dumps(coupling_metrics, indent=2) + "\n"
            prompt += "</coupling_metrics>\n\n"

        if import_edges:
            prompt += "<import_edges>\n"
            # Simplify import edges to avoid massive tokens
            for edge in import_edges:
                prompt += f"{edge[0]} -> {edge[1]}\n"
            prompt += "</import_edges>\n\n"

        prompt += "Return your synthesis as a structured Markdown document."
        return prompt
