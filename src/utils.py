import asyncio
from datetime import datetime, timedelta
import discord

def parseTimeString(currentTime, timeStr):
    try:
        # Attempt to parse time with AM/PM
        if any(x in timeStr.lower() for x in ['am', 'pm']):
            time = datetime.strptime(timeStr, "%I:%M%p" if ':' in timeStr else "%I%p")
        else:
            # Preliminary check for invalid hour ranges before attempting to parse
            if ':' in timeStr:
                hour, _, minute = timeStr.partition(':')
                hour = int(hour)
                minute = int(minute)
            else:
                hour = int(timeStr)
                minute = 0
            
            if hour < 0 or hour > 23:
                raise ValueError("Hour must be between 0 and 23 for 24-hour time format.")
            if minute < 0 or minute > 59:
                raise ValueError("Minute must be between 0 and 59.")
            
            # Create a datetime object using the valid hour and minute
            if (hour > 0 and (hour < 8 or (hour == 8 and minute == 0))):
                hour += 12
            time = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)

        # Replace the date part with today's date
        nextTime = time.replace(year=currentTime.year, month=currentTime.month, day=currentTime.day)
        
        # Check if the parsed time is in the past; if so, add one day
        if nextTime <= currentTime:
            nextTime += timedelta(days=1)

        return nextTime
    except ValueError as e:
        raise ValueError(f"Error parsing time: {str(e)}")
    
    
async def scheduleMessageAt(sendTime:datetime, client:discord.Client, channelId:int, message:str, condition=None):
    now = datetime.now()
    delay = (sendTime - now).total_seconds()
    await asyncio.sleep(delay)  # Wait until the scheduled time
    if (condition != None and not condition()): # Check if the condition is met
        return
    channel = client.get_channel(channelId)
    return await channel.send(message)


async def getUser(username:str, client:discord.Client):
    try:
        user = discord.utils.get(client.get_all_members(), name="username").id
    except discord.errors.NotFound:
        user = None
    return user