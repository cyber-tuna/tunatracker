#!/usr/bin/python3

import datetime
import json
import os
import requests
import sys
import time
import matplotlib.pyplot as plt
from io import BytesIO
import base64

from flask import Flask, request, redirect, render_template, session, url_for

app = Flask(__name__)

def generate_colors(num_colors):
    # Generate a list of colors using matplotlib's default color cycle
    return plt.cm.tab10.colors[:num_colors]

class Activity:
    def __init__(self, activity_type, year, distance, moving_time):
        self.activity_type = activity_type
        self.year = year
        self.distance = distance
        self.moving_time = moving_time

class Goal:
    def __init__(self, target_miles, target_moving_time, total_miles, total_moving_time):
        self.target_miles = target_miles
        self.target_moving_time = target_moving_time

        # Get the current date
        current_date = datetime.date.today()

        # Get the last day of the current year
        last_day_of_year = datetime.date(current_date.year, 12, 31)

        # Calculate the number of days remaining in the year
        remaining_days = (last_day_of_year - current_date).days

        # Calculate the number of weeks remaining
        weeks_remaining = remaining_days / 7

        remaining_miles = max(0, self.target_miles - total_miles)
        remaining_moving_time = max(0, self.target_moving_time - total_moving_time)

        self.miles_per_day = round(remaining_miles/remaining_days, 2)
        self.miles_per_week = round(remaining_miles/weeks_remaining, 2)

        self.moving_per_day = round(60*(remaining_moving_time/remaining_days), 2) # minutes
        self.moving_per_week = round(remaining_moving_time/weeks_remaining, 2)

        self.miles_percent_complete = round((total_miles/target_miles)*100, 1)
        self.moving_time_percent_complete = round((total_moving_time/target_moving_time)*100, 1)

class Stats:
    def __init__(self):
        self.years = set()
        self.activity_types = set()
        self.distance_by_year = {}
        self.total_mileage = 0
        self.total_moving_time = 0
        
        self.distance_per_activity = {}
        self.distance_per_year = {}
        self.distance_by_year_type = {}

        self.moving_time_per_activity = {}
        self.moving_time_per_year = {}
        self.moving_time_by_year_type = {}

        self.count_per_activity = {}
        self.count_per_year = {}
        self.count_by_year_type = {}

    def add_activity(self, activity):
        year = activity.year
        self.years.add(year)
        self.activity_types.add(activity.activity_type)

        self.distance_by_year.setdefault(activity.activity_type, 0)

        # Tally total distance by activity
        self.distance_per_activity.setdefault(activity.activity_type, 0)
        self.distance_per_activity[activity.activity_type] += activity.distance

        # Tally total distance by year
        self.distance_per_year.setdefault(year, 0)
        self.distance_per_year[year] += activity.distance

        # Tally total moving_time by activity
        self.moving_time_per_activity.setdefault(activity.activity_type, 0)
        self.moving_time_per_activity[activity.activity_type] += activity.moving_time

        # Tally activity count by activity
        self.count_per_activity.setdefault(activity.activity_type, 0)
        self.count_per_activity[activity.activity_type] += 1

        # Tally total moving_time by year
        self.moving_time_per_year.setdefault(year, 0)
        self.moving_time_per_year[year] += activity.moving_time

        # Tally activity count by year
        self.count_per_year.setdefault(year, 0)
        self.count_per_year[year] += 1

        # Tally distance by year type
        year = activity.year
        self.distance_by_year_type.setdefault(year, {})
        self.distance_by_year_type[year].setdefault(activity.activity_type, 0)
        self.distance_by_year_type[year][activity.activity_type] += activity.distance

        # Tally moving time by year type
        self.moving_time_by_year_type.setdefault(year, {})
        self.moving_time_by_year_type[year].setdefault(activity.activity_type, 0)
        self.moving_time_by_year_type[year][activity.activity_type] += activity.moving_time

        # Tally activity count by year type
        self.count_by_year_type.setdefault(year, {})
        self.count_by_year_type[year].setdefault(activity.activity_type, 0)
        self.count_by_year_type[year][activity.activity_type] += 1

    def get_years(self):
        return list(self.years)

    def get_activity_types(self):
        return list(self.activity_types)

    def get_total_distance_by_type(self, act_type):
        return int(self.distance_per_activity[act_type] * 0.000621371)

    def get_total_distance_by_year(self, year):
        return int(self.distance_per_year[year] * 0.000621371)

    def get_distance_by_year_type(self, year, act_type):
        return int(self.distance_by_year_type[year].get(act_type,0) * 0.000621371)

    
    def get_total_moving_time_by_type(self, act_type):
        return int(self.moving_time_per_activity[act_type] / 3600)

    def get_total_moving_time_by_year(self, year):
        return int(self.moving_time_per_year[year] / 3600)

    def get_moving_time_by_year_type(self, year, act_type):
        return int(self.moving_time_by_year_type[year].get(act_type,0) / 3600)


    def get_count_by_type(self, act_type):
        return int(self.count_per_activity[act_type])

    def get_count_by_year(self, year):
        return int(self.count_per_year[year])

    def get_count_by_year_type(self, year, act_type):
        return int(self.count_by_year_type[year].get(act_type,0))

        


def refresh_token():
    params = {'client_id': client_id,
              'client_secret': client_secret,
              'grant_type': 'refresh_token',
              'refresh_token': session['refresh_token']}
    
    res = requests.post("https://www.strava.com/oauth/token", params=params)

    session['access_token'] = json.loads(res.text)["access_token"]
    session['expires_at'] = json.loads(res.text)["expires_at"]
    session['refresh_token'] = json.loads(res.text)["refresh_token"]


@app.route("/authenticate")
def authenticate():
    server_url = os.environ.get("SERVER_URL", "localhost:5000")
    return redirect(f'http://www.strava.com/oauth/authorize?client_id={client_id}&response_type=code&redirect_uri=http://{server_url}/exchange_token&approval_prompt=force&scope=activity:read_all')


@app.route("/exchange_token")
def exchange_token():
    code = request.args.get('code')
    params = {'client_id': client_id,
              'client_secret': client_secret,
              'code': code,
              'grant_type': 'authorization_code'}
    
    res = requests.post("https://www.strava.com/oauth/token", params=params)

    session['access_token'] = json.loads(res.text)["access_token"]
    session['expires_at'] = json.loads(res.text)["expires_at"]
    session['refresh_token'] = json.loads(res.text)["refresh_token"]
    session['id'] = json.loads(res.text)["athlete"]["id"]

    return redirect(url_for('stats'))

@app.route("/stats")
def stats():
    activity_type_count = {}
    activity_distance_by_type = {}
    stats_by_year = {}
    mileage_by_year = {}

    access_token = session['access_token']

    headers = {'accept': 'application/json',
               'authorization': f'Bearer {access_token}'}
    activities = []
    page = 1

    if os.environ.get("DEBUG", None):
        with open("response", "r") as f:
            activities = json.loads(f.read())
    else:
        while True:
            params = {'per_page': '100',
                    'page': str(page)}
            res = requests.get('https://www.strava.com/api/v3/athlete/activities', params=params, headers=headers)
            if len(json.loads(res.text)) == 0:
                break
            activities.extend(json.loads(res.text))
            page += 1

    # with open('response', 'w') as f:
    #     f.write(json.dumps(activities))

    stats = Stats()
    plot_miles = {}
    plot_mt = {}

    for activity in activities:
        # tally up activity totals by type
        activity_type = activity["sport_type"]
        activity_type_count.setdefault(activity_type, 0)
        activity_type_count[activity_type] += 1

        # tally up activity distance by type
        activity_distance_by_type.setdefault(activity_type, 0)
        activity_distance_by_type[activity_type] += activity["distance"]

        # tally up yearly mileage and moving time
        year = datetime.datetime.strptime(activity["start_date"], "%Y-%m-%dT%H:%M:%SZ").year
        month = datetime.datetime.strptime(activity["start_date"], "%Y-%m-%dT%H:%M:%SZ").month
        stats_by_year.setdefault(year, [0,0]) # [distance, moving_time]
        stats_by_year[year][0] += activity["distance"]
        stats_by_year[year][1] += activity["moving_time"]

        activity_type = activity["sport_type"]

        # A hack for now to lump any activity using bike "Kinetic X or Kinetic GMC" into virtual rides.
        # Manually ascertained the gear ID
        if activity["gear_id"] in ["b11855420", "b8536861"] or \
           activity["trainer"]:
            activity_type = "VirtualRide"

        plot_miles.setdefault(year, [0] * 12)[month-1] += activity["distance"]
        plot_mt.setdefault(year, [0] * 12)[month-1] += activity["moving_time"]

        stats.add_activity(Activity(activity_type, year, activity["distance"], activity["moving_time"]))


    # plot mileage
    plt.figure(figsize=(15, 6))

    num_years = len(plot_miles)
    colors = generate_colors(num_years)

    for i, (year, data) in enumerate(plot_miles.items()):
        int_data = [int(x * 0.000621371) for x in data]
        plt.plot(range(1, 13), int_data, label=str(year), color=colors[i])

    plt.xlabel('Month')
    plt.ylabel('Miles Moved')
    plt.title('Monthly Miles Moved by Year')
    plt.xticks(range(1, 13), ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])
 
    maximum = max([int(max(data) * 0.000621371) for data in plot_miles.values()])
    plt.yticks(range(0, maximum + 1, 10))  # Adjust y-axis ticks
    plt.grid(color='lightgray', linestyle='-', linewidth=0.5)
    plt.legend()

    # Convert plot to base64 encoded image
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plot_data = base64.b64encode(buffer.getvalue()).decode()
    buffer.close()



    # plot moving time
    plt.clf()
    plt.figure(figsize=(15, 6))

    num_years = len(plot_mt)
    colors = generate_colors(num_years)

    for i, (year, data) in enumerate(plot_mt.items()):
        int_data = [int(x / 3600) for x in data]
        plt.plot(range(1, 13), int_data, label=str(year), color=colors[i])

    plt.xlabel('Month')
    plt.ylabel('Moving Time')
    plt.title('Monthly Moving Time by Year')
    plt.xticks(range(1, 13), ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])
    
    maximum = max([int(max(data) / 3600) for data in plot_mt.values()])
    plt.yticks(range(0, maximum + 1, 2))  # Adjust y-axis ticks
    plt.grid(color='lightgray', linestyle='-', linewidth=0.5)
    plt.legend()

    # Convert plot to base64 encoded image
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plot_data2 = base64.b64encode(buffer.getvalue()).decode()
    buffer.close()


    # Convert to miles
    for key in activity_distance_by_type:
        activity_distance_by_type[key] = str(int(float(activity_distance_by_type[key]) * 0.000621371))

    # Convert to miles and seconds
    for key in stats_by_year:
        stats_by_year[key][0] = str(int(float(stats_by_year[key][0]) * 0.000621371))
        stats_by_year[key][1] = str(int(float(stats_by_year[key][1]) / 3600))

    result = ""
    result += json.dumps(activity_type_count) + "\n"
    result += json.dumps(activity_distance_by_type)

    year = datetime.datetime.now().year
    goal_miles = int(os.environ.get("GOAL_MILES", 100))
    goal_moving = int(os.environ.get("GOAL_MOVING", 100))
    goal = Goal(goal_miles, goal_moving, stats.get_total_distance_by_year(year), stats.get_total_moving_time_by_year(year))

    print("MMILES PER DAY", goal.miles_per_day)
    print("MMILES PER WEEK", goal.miles_per_week)
    print("Percent Complete miles", goal.miles_percent_complete)
    print("Percent Complete time", goal.moving_time_percent_complete)


    return render_template('stats.html', stats=stats, goal=goal, mile_plot=plot_data, moving_time_plot=plot_data2)


@app.route("/")
def index():
    if 'id' in session:
        print("id in session", session['id'])
        # if int(time.time()) >= session['expires_at']:
        if True:
            print("refreshing token")
            refresh_token()
        return redirect(url_for('stats'))
    else:
        return render_template('index.html', image_url='/static/btn_strava_connectwith_light.png', link_url="authenticate")


# main driver function
if __name__ == '__main__':
    client_id = os.environ.get("CLIENT_ID", None)
    client_secret = os.environ.get("CLIENT_SECRET", None)
    app_secret = os.environ.get("APP_SECRET", None)

    if not client_id:
        print("ERROR: CLIENT_ID not set")
        sys.exit()
    if not client_secret:
        print("ERROR: CLIENT_SECRET not set")
        sys.exit()
    if not app_secret:
        print("ERROR: APP_SECRET not set")
        sys.exit()

    app.secret_key = app_secret
    app.run(host='0.0.0.0', debug=True)


