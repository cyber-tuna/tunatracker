# Usage

```bash
GOAL_MILES=<mileage goal> GOAL_MOVING=<moving time goal> HOST=<server URL> APP_SECRET=<app secret> CLIENT_ID=<client ID>  CLIENT_SECRET=<client secret> python3 tunatracker.py
```

Configuration:
* `CLIENT_ID`, `CLIENT_SECRET`: Found at Strava.com under settings->My API Application
* `APP_SERET`: A random value provided to flask for cookie signing
* `SERVER_URL`: The URL and port to which Strava will redirect the user after authentication. Defaults to "localhost:5000"
* `GOAL_MILES`: Mileage goal for the current year
* `GOAL_MOVING` : Moving time (in hours) goal for the current year
* `DEBUG`: Optional debug flag. If set, a local cached version of activity data will be used instead of retrieveing from the Strava API

