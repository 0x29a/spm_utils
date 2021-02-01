"""
Returns list of tickets that were inserted after deadline.
"""

import os
import re

from datetime import datetime, timedelta, timezone
from functools import lru_cache

from dotenv import load_dotenv
from jira import JIRA

load_dotenv()

username = os.getenv("JIRA_USERNAME")
password = os.getenv("JIRA_PASSWORD")
project_prefix = os.getenv("PROJECT_PREFIX")
project_name = os.getenv("PROJECT_NAME")

JIRA_URL = "https://tasks.opencraft.com"
SPRINT_REGEX = r"\b[A-Z]{2,3}\.\d{3}"
JIRA_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f%z"

jira = JIRA(JIRA_URL, auth=(username, password))


@lru_cache(maxsize=1)
def get_current_sprint_code():
    issues_in_current_sprint = jira.search_issues(
        "project={} AND SPRINT not in closedSprints() AND sprint not in futureSprints()".format(
            project_name
        )
    )

    sprint_field = issues_in_current_sprint[0].fields.customfield_10005[0]
    sprint_code = re.findall(SPRINT_REGEX, sprint_field)[0]

    return sprint_code


@lru_cache(maxsize=1)
def get_next_sprint_code():
    """
    Some dirty hack here because JQL has no ability to retreive next future sprint.

    I retrieve first ticket from the current sprint, then get `customfield_10005`, which
    contains sprint in format `BB.xxx`, then increment it and return.
    """

    current_sprint_code = get_current_sprint_code()

    sprint_number = int(current_sprint_code.split(".")[1])
    next_sprint_number = sprint_number + 1
    next_sprint_code = f"{project_prefix}.{next_sprint_number}"

    return next_sprint_code


def get_ticket_creation_deadline():
    """
    Returns datetime object that represents ticket creation/addition deadline.
    """

    # I need this constants to know exactly what is "thursday of second week of current sprint".
    sprint_239_number = 239
    sprint_239_start_datetime = datetime(
        year=2021,
        month=1,
        day=26,
        hour=0,
        minute=0,
        second=0,
        tzinfo=timezone.utc,
    )

    current_sprint_number = int(get_current_sprint_code().split(".")[1])
    sprint_numbers_diff = current_sprint_number - sprint_239_number
    current_sprint_start_datetime = sprint_239_start_datetime + timedelta(
        days=sprint_numbers_diff * 14
    )

    days_from_start_sprint_to_end_of_thursday = timedelta(days=10)
    ticket_creation_deadline = (
        current_sprint_start_datetime + days_from_start_sprint_to_end_of_thursday
    )

    return ticket_creation_deadline


def get_tickets_in_next_sprint():
    return jira.search_issues(f"sprint={get_next_sprint_code()}", expand="changelog")


def ticket_insertion_date(ticket):
    """
    Checks changelog for ticket to find when it was added to sprint.

    Otherwise, returns ticket creation date.
    """

    sprint_item_field_name = "Sprint"
    not_sprint = (
        "Stretch Goals",
        "Backlog",
        "Long External Review/Blocked",
        "",
    )

    ticket_created = datetime.strptime(ticket.fields.created, JIRA_TIME_FORMAT)

    transition_to_current_sprint_date = None

    histories = ticket.changelog.histories
    for history in histories:
        items = history.items
        for item in items:
            if item.field == sprint_item_field_name:
                if item.toString is not None and item.toString not in not_sprint:
                    sprint_code = re.findall(SPRINT_REGEX, item.toString)[0]
                    if sprint_code == get_next_sprint_code():
                        transition_to_current_sprint_date = datetime.strptime(
                            history.created, JIRA_TIME_FORMAT
                        )

    if transition_to_current_sprint_date is None:
        print(f"WARNING: No transition to current sprint found for {ticket.key}.")

    return transition_to_current_sprint_date or ticket_created


def ticket_inserted_after_deadline(ticket):
    inserted = ticket_insertion_date(ticket)
    deadline = get_ticket_creation_deadline()

    return inserted > deadline


def print_ticket_inserted_after_deadline():
    tickets_in_the_next_sprint = get_tickets_in_next_sprint()

    results = []

    for ticket in tickets_in_the_next_sprint:
        print(f"Checking {ticket.key}.")
        if ticket_inserted_after_deadline(ticket):
            results.append(ticket)

    print("=" * 200, "\n")

    if results:
        print("\n".join(ticket.key for ticket in results))
    else:
        print("Yay! No inserted tickets found.")


def main():
    print_ticket_inserted_after_deadline()


if __name__ == "__main__":
    main()
