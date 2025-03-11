import os

import discord
import requests
from discord.ext import tasks
from loguru import logger

base_url = "https://mygo-api.yichen0403.us.kg/api"
API_TOKEN = os.getenv("API_TOKEN")


@tasks.loop(minutes=15)
async def update_status(bot):
    server_count = len(bot.guilds)
    app_info = await bot.application_info()
    user_count = app_info.approximate_user_install_count
    response = requests.get(f"{base_url}/ranks/total")
    if response.status_code == 200:
        data = response.json()
        await bot.change_presence(
            activity=discord.CustomActivity(
                # TODO: verify translation
                name="GO {data['total_times']} times | {server_count} servers"
            )
        )
        logger.info(
            f"The server status has been updated to: GO {data['total_times']} times | {server_count} servers"
        )
        response = requests.post(
            f"{base_url}/record_server_count",
            json={"server_count": server_count, "user_count": user_count},
        )
        if response.status_code == 200:
            logger.info(f"Server status update successfully: {response.status_code}")
        else:
            logger.error(f"Server status update failed: {response.status_code}")

    else:
        logger.error(f"Server status update failed: {response.status_code}")


def record(text):
    text = text[0]
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_TOKEN}",
    }
    response = requests.post(f"{base_url}/ranks", json=text, headers=headers)
    if response.status_code == 200:
        logger.info(f"status code : {response.status_code} Data updated")
    else:
        logger.error(f"status code : {response.status_code} Data update failed")
