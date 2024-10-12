import asyncio
import niquests

from viam.robot.client import RobotClient
from viam.components.board import Board

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    api_key: str = ""
    api_key_id: str = ""
    address: str = ""

    sensor_pin: str = "8"
    buzzer_pin: str = "23"

    ntfy_server: str = "https://ntfy.sh"
    ntfy_topic: str = "home_alerts"

    model_config = SettingsConfigDict(env_file=".env")


class Notifier:
    def __init__(self, server: str, default_topic: str):
        self.server = server
        self.default_topic = default_topic

    def send(self, message: str, topic: str | None = None):
        topic = topic or self.default_topic

        niquests.post(f"{self.server}/{topic}", data=message.encode(encoding="utf-8"))


async def connect(settings: Settings):
    opts = RobotClient.Options.with_api_key(
        # Replace "<API-KEY>" (including brackets) with your machine's api key
        api_key=settings.api_key,
        # Replace "<API-KEY-ID>" (including brackets) with your machine's api key id
        api_key_id=settings.api_key_id,
    )
    return await RobotClient.at_address(settings.address, opts)


async def main():
    settings = Settings()
    notifier = Notifier(server=settings.ntfy_server, default_topic=settings.ntfy_topic)
    machine = await connect(settings)

    state = "no_leak"

    # Note that the pin supplied is a placeholder. Please change this to a valid pin you are using.
    # pi
    pi = Board.from_robot(machine, "pi")
    sensor = await pi.digital_interrupt_by_name(settings.sensor_pin)
    buzzer = await pi.gpio_pin_by_name(settings.buzzer_pin)

    async for tick in await pi.stream_ticks([sensor]):
        if tick.high and state == "no_leak":
            await buzzer.set_pwm_frequency(423)
            await buzzer.set_pwm(0.5)

            notifier.send("A leak has been detected in the upstairs bathroom!")
            state = "leak_detected"
        elif (not tick.high) and state == "leak_detected":
            await buzzer.set_pwm(0.0)
            notifier.send("The leak has been resolved")
            state = "no_leak"

    # Don't forget to close the machine when you're done!
    await machine.close()


if __name__ == "__main__":
    asyncio.run(main())
