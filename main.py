from datetime import datetime

from telethon import TelegramClient, events, errors
from telethon.tl.functions.users import GetFullUserRequest
import asyncio
import hashlib
import time
import os
from dotenv import load_dotenv

load_dotenv()

api_id = os.environ.get("API_ID")
api_hash = os.environ.get("API_HASH")
goal_user_id = os.environ.get("USER_ID")
Channel_ID = int(os.environ.get("CHANNEL_ID"))   # for saving log

STATUS_FILE = os.path.expanduser("./last_status_id.txt")

client = TelegramClient('session_name', api_id, api_hash)

async def main():

    def generate_forensic_log(entry):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {entry}"

        # Erzeuge einen SHA-256 Hash dieser Zeile
        hash_object = hashlib.sha256(log_line.encode())
        hex_dig = hash_object.hexdigest()

        # Schreibe Log und den dazugehörigen Hash in eine separate Datei
        with open("forensic_log.txt", "a") as f:
            f.write(f"{log_line} | HASH: {hex_dig}\n")

    async def get_user_details(user_id):
        try:
            full_user = await client(GetFullUserRequest(user_id))
            user = full_user.users[0]
            print(f"Name: {user.first_name} {user.last_name}")
            print(f"Username: @{user.username}")
            print(f"Bio: {full_user.full_user.about}")
            print(f"Letztes Mal online: {user.status}")
        except Exception as e:
            print(f"Fehler: {e} (Möglicherweise Profil privat oder ID ungültig)")

    @client.on(events.NewMessage(from_users=goal_user_id))
    async def handler(event):
        msg_text = event.text or "[Kein Text/Medium]"
        sender = await event.get_sender()
        name = f"{sender.first_name} {sender.last_name or ''}"

        log_content = f"User-ID: {event.sender_id} - Name: {name}\nID: {event.id}\nNEU\nText: {msg_text}"

        # Lokale Sicherung (wie zuvor)
        generate_forensic_log(f"NEU: {log_content}")

        # Externe Sicherung via E-Mail (Forensischer Zeitstempel)
        #send_forensic_email(f"TELEGRAM BEWEIS - ID {event.id}", log_content)

        # Nachricht in den Channel schicken
        await client.send_message(Channel_ID, log_content)
        if event.media:
            await client.forward_messages(Channel_ID, event.message)

    @client.on(events.MessageEdited(from_users=goal_user_id))
    async def edit_handler(event):
        msg_text = event.text or "[Kein Text/Medium]"
        sender = await event.get_sender()
        name = f"{sender.first_name} {sender.last_name or ''}"

        log_content = f"User-ID: {event.sender_id} - Name: {name}\nID: {event.id}\nÄNDERUNG/Reaktion!\nText: {msg_text}"

        generate_forensic_log(log_content)
        # send_forensic_email(f"MANIPULATION - ID {event.id}", log_content)
        await client.send_message(Channel_ID, log_content)

        if event.media:
            await client.forward_messages(Channel_ID, event.message)

    async def send_status_alarm(message):
        print(f"ALARM: {message}")

    async def check_connection(client):
        """Check if client is connected to Telegram servers."""
        while True:
            try:
                if not client.is_connected():
                    await send_status_alarm("Lost connection to Telegram servers. Attempting to reconnect...")
                    await client.connect()
                else:
                    # optional: log connection status
                    print("Verbindung zum Telegram-Server hergestellt.")
                    await update_status_msg(client, Channel_ID)
            except Exception as e:
                await send_status_alarm(f"Connection error: {e}")
            finally:
                await asyncio.sleep(30)

    async def update_status_msg(client, channel_id):
        old_msg_id = None
        # load last status ID
        if os.path.exists(STATUS_FILE):
            with open(STATUS_FILE, "r") as f:
                content = f.read().strip()
                if content:
                    old_msg_id = int(content)
        # delete old status message if there is oen
        if old_msg_id:
            try:
                await client.delete_messages(channel_id, old_msg_id)
            except Exception:
                pass  # Nachricht wurde vielleicht schon manuell gelöscht

        # save newest status ID
        now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        new_msg = await client.send_message(
            channel_id,
            f"🟢 **System-Check:** Skript ist aktiv.\nLetzter Reconnect: {now}"
        )

        # 4. Neue ID für das nächste Mal speichern
        with open(STATUS_FILE, "w") as f:
            f.write(str(new_msg.id))

    # Client start (asynchron)
    await client.start()
    print("Client gestartet.")
    client.loop.create_task(check_connection(client))
    # Wait until programm is finished
    await client.run_until_disconnected()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nScript beendet.")