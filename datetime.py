from datetime import datetime

##datetime object containing current date and time
now = datetime.now()
print("now =", now)

# Extract seconds as a float and round to two decimal places
seconds = int(round(now.second + now.microsecond / 1_000_000, 0))


##YYYY-mm-dd %H:m:s
# Format the date and time, excluding microseconds
dt_string = now.strftime("%Y-%m-%d %H:%M:") + f"{seconds:2d}"
print("current date & time =", dt_string)
