import os
import re

from dotenv import load_dotenv
from jira import JIRA

load_dotenv()

username = os.getenv("JIRA_USERNAME")
password = os.getenv("JIRA_PASSWORD")
project_prefix = os.getenv("PROJECT_PREFIX")
project_name = os.getenv("PROJECT_NAME")

jira = JIRA("https://tasks.opencraft.com", auth=(username, password))

issues_in_current_sprint = jira.search_issues(
    "project={} AND SPRINT not in closedSprints() AND sprint not in futureSprints()".format(
        project_name
    )
)

sprint_regex = r"{prefix}\.\d{{3}}".format(prefix=project_prefix)
sprint_field = issues_in_current_sprint[0].fields.customfield_10005[0]
sprint_string = re.findall(sprint_regex, sprint_field)[0]
sprint_number = int(sprint_string.split(".")[1])
next_sprint_number = sprint_number + 1
next_sprint_code = "{}.{}".format(project_prefix, next_sprint_number)

yellow_issues = jira.search_issues(
    'sprint={} and "Ready for a sprint" = 0'.format(next_sprint_code)
)

to_check = [
    ("Yellow tickets", '"Ready for a sprint" = 0'),
    ("Flagged tickets", "flagged != null"),
    ("Tickets without assignees or reviewers", '(assignee = null) and ("Reviewer 1" = null)'),
    ("Tickets without reviewers", '("Reviewer 1" = null) and (assignee != null)'),
    ("Tickets without assignees", '("Reviewer 1" != null) and (assignee = null)'),
    (
        "Tickets without remaining estimate",
        "(remainingEstimate = 0 or remainingEstimate = null)",
    ),
    ("Tickets without story points", '"Story Points" = null'),
]

for text, query in to_check:
    grouped = {}
    issues = jira.search_issues("sprint={} and {}".format(next_sprint_code, query))
    
    for issue in issues:
        to_ping = issue.fields.assignee or issue.fields.reporter
        grouped.setdefault(to_ping, []).append(issue.key)

    print('\n\n\n')
    print('—' * 200)
    print(f'{text}')
    print('—' * 200)
    for to_ping, keys in grouped.items():
        print(f'****** To ping: {to_ping}')
        print(
            "\n".join(
                [
                    "https://tasks.opencraft.com/browse/{key}".format(
                        key=key
                    )
                    for key in keys
                ]
            )
        )
