from os import environ as env
from flask import Flask
from flask_slack import Slack
import requests

# env vars
rancher_url = env.get('RANCHER_URL', env.get('CATTLE_URL'))
rancher_access_key = env.get('RANCHER_ACCESS_KEY', env.get('CATTLE_ACCESS_KEY'))
rancher_secret_key = env.get('RANCHER_SECRET_KEY', env.get('CATTLE_SECRET_KEY'))
rancher_stacks = env.get('RANCHER_STACKS')
slash_token = env.get('SLASH_TOKEN')
slash_command = env.get('SLASH_COMMAND')
team_id = env.get('TEAM_ID')

# app bootstrap
app = Flask(__name__)
slack = Slack(app)
app.add_url_rule('/', view_func=slack.dispatch)

green = "good"
yellow = "warning"
red = "danger"
state_color = {
    "active": green,
    "upgraded": green,
    "initializing": yellow,
    "inactive": red,
    "unhealthy": red,
}

def create_attachments(states):
    attachments = []
    for state in states:
        services = states[state]
        services.sort()
        title = "%d %s services" % (len(services), state)
        text = "\n".join(services)

        attachments += [{
            "title": title,
            "fallback": title,
            "color": state_color.get(state, None),
            "text": text,
        }]

    return attachments

@slack.command(slash_command, token=slash_token, team_id=team_id, methods=['GET', 'POST'])
def check_services(**kwargs):
    auth = (rancher_access_key, rancher_secret_key)

    states = {}
    for stack_name in rancher_stacks.split(','):
        url = "%s/stacks?name=%s" % (rancher_url, stack_name)
        stack = requests.get(url, auth=auth).json()['data'][0]

        url = stack['links']['services']
        services = requests.get(url, auth=auth).json()['data']

        for service in services:
            state = service["state"]
            if state not in states:
                states[state] = []
            states[state] += [service["name"]]

    attachments = create_attachments(states)

    return slack.response(slash_command, response_type="in_channel", attachments=attachments)


# app run
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
