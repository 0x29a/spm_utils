import os
import re

from dotenv import load_dotenv
from jira import JIRA

load_dotenv()

username = os.getenv("JIRA_USERNAME")
password = os.getenv("JIRA_PASSWORD")

jira = JIRA("https://tasks.opencraft.com", auth=(username, password))

issues_in_current_sprint = jira.search_issues(
  'project=Bebop AND SPRINT not in closedSprints() AND sprint not in futureSprints()'
)

sprint_regex = r'BB\.\d{3}'
sprint_field = issues_in_current_sprint[0].fields.customfield_10005[0]
sprint_string = re.findall(sprint_regex, sprint_field)[0]
sprint_number = int(sprint_string.split('.')[1])
next_sprint_number = sprint_number + 1
next_sprint_code = 'BB.' + str(next_sprint_number)

yellow_issues = jira.search_issues('sprint={} and "Ready for a sprint" = 0'.format(next_sprint_code))

to_check = [
  ('Yellow tickets', '"Ready for a sprint" = 0'),
  ('Flagged tickets', 'flagged != null'),
  ('Tickets without reviewers', '"Reviewer 1" = null'),
  ('Tickets without remaining estimate', '(remainingEstimate = 0 or remainingEstimate = null)'),
  ('Tickets without story points', '"Story Points" = null'),
]

for text, query in to_check:
  issues = jira.search_issues('sprint={} and {}'.format(next_sprint_code, query))
  print(
    '{}:\n{}\n'.format(
      text,
      '\n'.join([issue.key for issue in issues])
    )
  )
