from datetime import datetime, timezone

def build_world(guild, channel, recent_messages):
    now=datetime.now().astimezone()
    return {
        "home": "Brix Community",
        "home_guild_id": guild.id if guild else None,
        "server_name": guild.name if guild else None,
        "channel_name": channel.name if hasattr(channel, "name") else None,
        "channel_id": channel.id,
        "local_time": now.isoformat(),
        "date": now.date().isoformat(),
        "weekday": now.strftime("%A"),
        "hour": now.hour,
        "minute": now.minute,
        "recent_activity_count": len(recent_messages),
    }
