import os.path
import time
import sys
import datetime
import dataclasses
import yaml

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

@dataclasses.dataclass
class Event:
    summary: str
    start: str
    end: str = "EOD"

def add_break_event(agenda):
    new_agenda = []
    for i in range(len(agenda)):
        current_event = agenda[i]
        new_agenda.append(current_event)

        try:
            next_event = agenda[i + 1]
        except IndexError:
            new_agenda.append(Event("END",
                                    current_event.end))
            break

        if current_event.end != next_event.start:
            new_agenda.append(Event("BREAK",
                                    current_event.end,
                                    next_event.start))
    return new_agenda

def main():
    config = None
    creds = None

    with open("config.yaml") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    date = sys.argv[1]

    offset = time.timezone if time.daylight else time.altzone
    sign = "+" if (offset * -1) > 0 else "-"
    timezone = "{}{:02d}:00".format(sign, int(abs(offset) / 3600))

    try:
        agenda = []
        service = build('calendar', 'v3', credentials=creds)
        for calendar_id in config["calendarIds"]:
            # Call the Calendar API
            for event in service.events().list(
                    calendarId=calendar_id, singleEvents=True,
                    timeMin="{}T00:00:00{}".format(date, timezone),
                    timeMax="{}T23:59:00{}".format(date, timezone),
                    orderBy='startTime').execute().get('items', []):
                start = datetime.datetime.fromisoformat(
                    event["start"]["dateTime"]).strftime("%H:%M")
                end = datetime.datetime.fromisoformat(
                    event["end"]["dateTime"]).strftime("%H:%M")
                agenda.append(Event(event["summary"], start, end))
        # Sort by starting time
        agenda.sort(key = lambda x: x.start)
        # Add BREAK events
        agenda = add_break_event(agenda)
        # Print
        for event in agenda:
            print("- [ ] {} {} ({})".format(
                event.start,
                event.summary,
                event.end))
    except HttpError as error:
        print('An error occurred: %s' % error)

if __name__ == '__main__':
    main()
