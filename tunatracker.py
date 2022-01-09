#!/usr/bin/python3

import datetime
import json
import os
import requests
import sys

from flask import Flask, request, redirect, render_template

app = Flask(__name__)

@app.route("/authenticate")
def authenticate():              
    return redirect(f'http://www.strava.com/oauth/authorize?client_id={client_id}&response_type=code&redirect_uri=http://localhost:5000/exchange_token&approval_prompt=force&scope=activity:read_all')

@app.route("/exchange_token")
def exchange_token():
    code = request.args.get('code')
    params = {'client_id': client_id,
              'client_secret': client_secret,
              'code': code,
              'grant_type': 'authorization_code'}
    
    res = requests.post("https://www.strava.com/oauth/token", params=params)
    access_token = json.loads(res.text)["access_token"]

    activity_type_count = {}
    activity_distance_by_type = {}
    stats_by_year = {}

    headers = {'accept': 'application/json',
               'authorization': f'Bearer {access_token}'}

    activities = []

    page = 1
    while True:
        params = {'per_page': '100',
                'page': str(page)}
        res = requests.get('https://www.strava.com/api/v3/athlete/activities', params=params, headers=headers)
        if len(json.loads(res.text)) == 0:
            break
        activities.extend(json.loads(res.text))
        page += 1

    # with open("response", "r") as f:
    #     activities = json.loads(f.read())

    for activity in activities:
        # tally up activity totals by type
        activity_type = activity["type"]
        activity_type_count.setdefault(activity_type, 0)
        activity_type_count[activity_type] += 1

        # tally up activity distance by type
        activity_distance_by_type.setdefault(activity_type, 0)
        activity_distance_by_type[activity_type] += activity["distance"]

        # tally up yearly mileage
        year = datetime.datetime.strptime(activity["start_date"], "%Y-%m-%dT%H:%M:%SZ").year
        stats_by_year.setdefault(year, 0)
        stats_by_year[year] += activity["distance"]

    # Convert to miles
    for key in activity_distance_by_type:
        activity_distance_by_type[key] = str(int(float(activity_distance_by_type[key]) * 0.000621371))

    # Convert to miles
    for key in stats_by_year:
        stats_by_year[key] = str(int(float(stats_by_year[key]) * 0.000621371))

    result = ""
    result += json.dumps(activity_type_count) + "\n"
    result += json.dumps(activity_distance_by_type)
    return render_template('stats.html', activities=activity_type_count, distance=activity_distance_by_type, year=stats_by_year)

@app.route("/")
def hello_world():
    return "<a href=\"/authenticate\">Authenticate</a>"


# main driver function
if __name__ == '__main__':
    client_id = os.environ.get("CLIENT_ID", None)
    client_secret = os.environ.get("CLIENT_SECRET", None)

    if not client_id:
        print("ERROR: CLIENT_ID not set")
        sys.exit()
    if not client_secret:
        print("ERROR: CLIENT_SECRET not set")
        sys.exit()

    app.run(host='0.0.0.0', port=80, debug=True)


