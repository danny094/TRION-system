"""Shared P11 list-to-logs prompt cases for offline and gated live tests."""
from __future__ import annotations

from typing import NamedTuple


class PromptCase(NamedTuple):
    case_id: str
    language: str
    target_kind: str
    template: str


DE_CASES = (
    PromptCase("de-01", "de", "id", "Welche Container laufen und zeige mir anschließend die Logzeilen von {target}."),
    PromptCase("de-02", "de", "id", "Welche Container sind aktiv? Zeige mir danach die Logs des Containers {target}."),
    PromptCase("de-03", "de", "id", "Welche Container laufen? Zeige anschließend die Logs vom Container {target}."),
    PromptCase("de-04", "de", "id", "Zeige, welche Container aktiv sind, und danach die Logs für Container {target}."),
    PromptCase("de-05", "de", "id", "Welche Container laufen? Hole danach die Logs für den Container {target}."),
    PromptCase("de-06", "de", "id", "Bitte prüfe, welche Container laufen, und gib die Logzeilen des Containers {target} aus."),
    PromptCase("de-07", "de", "id", "Was läuft gerade? Zeige anschließend die Logs von Container {target}."),
    PromptCase("de-08", "de", "id", "Welche Container laufen? Zeige danach Logs für die Container-ID {target}."),
    PromptCase("de-09", "de", "id", "Welche Container sind aktiv? Zeige dann die Logs des Containers mit der ID {target}."),
    PromptCase("de-10", "de", "id", "Ermittle, welche Container laufen. Lies danach die Logs vom Container mit der ID {target}."),
    PromptCase("de-11", "de", "id", "Welche Container laufen? Gib anschließend das Protokoll von Container {target} aus."),
    PromptCase("de-12", "de", "id", "Welche Container sind aktiv und was steht in den Logs fuer {target}?"),
    PromptCase("de-13", "de", "name", "Welche Container laufen und zeige mir die Logs des Containers {target}."),
    PromptCase("de-14", "de", "name", "Welche Container sind aktiv? Zeige danach die Logs von {target}."),
    PromptCase("de-15", "de", "name", "Welche Container laufen? Gib anschließend die Logzeilen für den Container {target} aus."),
    PromptCase("de-16", "de", "name", "Was läuft gerade? Zeige danach das Protokoll des Containers {target}."),
)


EN_CASES = (
    PromptCase("en-01", "en", "id", "Which containers are running? Then show the logs for container {target}."),
    PromptCase("en-02", "en", "id", "List the running containers and afterwards display the logs from container {target}."),
    PromptCase("en-03", "en", "id", "Show which containers are active, then retrieve the logs of container {target}."),
    PromptCase("en-04", "en", "id", "Which containers are running? Read the logs for the container {target} afterwards."),
    PromptCase("en-05", "en", "id", "Find the active containers and then show logs for container ID {target}."),
    PromptCase("en-06", "en", "id", "Tell me which containers are running and show the logs for the container with ID {target}."),
    PromptCase("en-07", "en", "id", "First list the running containers; next display logs from the container with ID {target}."),
    PromptCase("en-08", "en", "id", "Check which containers are active. Then fetch the log lines for container {target}."),
    PromptCase("en-09", "en", "id", "Show active containers, followed by the logs of container ID {target}."),
    PromptCase("en-10", "en", "id", "Which containers are running, and what do the logs for {target} say?"),
    PromptCase("en-11", "en", "id", "List containers that are active and then read the log output from {target}."),
    PromptCase("en-12", "en", "id", "Please show the running containers before displaying the logs for {target}."),
    PromptCase("en-13", "en", "name", "Which containers are running? Then show the logs for container {target}."),
    PromptCase("en-14", "en", "name", "List the active containers and display the logs from {target} afterwards."),
    PromptCase("en-15", "en", "name", "Show which containers are running and then retrieve {target}'s logs."),
    PromptCase("en-16", "en", "name", "Which containers are active? Afterwards, read the logs of the container named {target}."),
)


POSITIVE_CASES = (*DE_CASES, *EN_CASES)


def render_prompt(case: PromptCase, *, container_id: str, container_name: str) -> tuple[str, str]:
    target = container_id if case.target_kind == "id" else container_name
    return case.template.format(target=target), target
