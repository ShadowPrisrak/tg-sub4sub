from telethon import TelegramClient, events
from telethon.tl.functions.channels import JoinChannelRequest, GetParticipantRequest, LeaveChannelRequest
from telethon.tl.functions.account import UpdateNotifySettingsRequest
from telethon.tl.functions.contacts import BlockRequest
import config
import asyncio
import random
import re

client = TelegramClient("my_account", config.api_id, config.api_hash)

MY_CHANNEL_LINK = "https://t.me/alfarefs"
MY_CHANNEL_USERNAME = "@alfarefs"  # ОБЯЗАТЕЛЬНО ВПИШИ СЮДА НИК СВОЕГО КАНАЛА (с @)

BLACKLIST_WORDS = ["отзыв", "отзывы", "review", "реакци", "реакция"]
DONE_WORDS = ["готово", "спасибо", "ок", "принял", "благодарю", "окей", "сделал", "+", "++", "всё", "все", "сделала"]

# База данных в памяти (кому бот что подписал)
watched_users = {}  # {user_id: channel_username}


@client.on(events.NewMessage(incoming=True))
async def handler(event):
    if not event.is_private:
        return
    sender = await event.get_sender()
    if sender.bot:
        return

    text = event.raw_text.lower()
    print(f"Новое сообщение от @{sender.username}: {text}")

    # Проверка на завершение диалога
    if any(word == text.strip() for word in DONE_WORDS) or text.strip() in DONE_WORDS:
        print(f"Диалог с @{sender.username} закрыт.")
        return  # Просто игнорим, ничего не отвечаем

    # Если чел уже в нашей базе, проверим его подписку на наш канал
    if sender.id in watched_users:
        try:
            my_channel = await client.get_entity(MY_CHANNEL_USERNAME)
            # Проверяем, подписан ли чел на НАШ канал
            await client(GetParticipantRequest(channel=my_channel, participant=sender.id))
            print(f"✅ @{sender.username} подписан на наш канал. Всё ок.")
            del watched_users[sender.id]  # Убираем из базы, он молодец
        except Exception:
            # Если не подписан - отписываемся от его канала и ругаемся
            print(f"❌ @{sender.username} НЕ подписался на наш канал. Отписываюсь от @{watched_users[sender.id]}")
            try:
                ch = await client.get_entity(watched_users[sender.id])
                await client(LeaveChannelRequest(ch))
                await event.reply(
                    "Ты не подписался на мой канал, так что я отписался от твоего. Взаимный пиар должен быть честным.")
            except Exception as e:
                print(f"Ошибка отписки: {e}")
            del watched_users[sender.id]
            return

    # 1. ЧС и фильтры
    if any(word in text for word in BLACKLIST_WORDS):
        if "отзыв" in text or "review" in text:
            print(f"⛔ Кидаю в ЧС @{sender.username} за отзывы")
            try:
                await client(BlockRequest(id=sender.id))
                await event.reply("Взаимные подписки только. Отзывы не пишу. Блокирую.")
            except:
                pass
            return
        elif "реакци" in text:
            print(f"⚠️ @{sender.username} просит реакции, отказываю")
            await event.reply("Браток, реакции ставить не могу, только подписка. Скинь ссылку на канал.")
            return

    # 2. Парсинг ссылки
    link_match = re.search(r'(?:t\.me|telegram\.me)/([a-zA-Z0-9_]+)', text)
    if link_match:
        channel_username = link_match.group(1)
        if channel_username.lower().endswith("bot"):
            await event.reply("Это бот, а не канал. Кидай ссылку на канал.")
            return

        print(f"Найдена ссылка: @{channel_username}. Жду...")
        await asyncio.sleep(random.randint(10, 30))

        try:
            channel = await client.get_entity(channel_username)
            await client(JoinChannelRequest(channel))

            from telethon.tl.types import InputPeerNotifySettings
            await client(UpdateNotifySettingsRequest(
                peer=channel, settings=InputPeerNotifySettings(mute_until=2147483647)
            ))

            try:
                from telethon.tl.functions.folders import EditPeerFoldersRequest
                from telethon.tl.types import InputFolderPeer
                peer = await client.get_input_entity(channel)
                await client(EditPeerFoldersRequest(
                    folder_peers=[InputFolderPeer(peer=peer, folder_id=1)]
                ))
            except Exception:
                pass

            # Запоминаем, что подписались, чтобы потом проверить взаимность
            watched_users[sender.id] = channel_username

            await asyncio.sleep(random.randint(3, 7))
            await event.reply(f"Готово! Подписался на @{channel_username}. Вот мой канал: {MY_CHANNEL_LINK}")
            print(f"✅ Все сделал для @{sender.username}")

        except Exception as e:
            print(f"❌ Ошибка: {e}")
            await event.reply("Чет не могу подписаться. Проверь ссылку или канал закрытый.")

    else:
        if len(text) < 15:
            await event.reply("Привет! Скидывай ссылку на свой канал, я подпишусь и скину свою.")


# Запуск с красивым закрытием
async def main():
    me = await client.get_me()
    print(f"Бот запущен на акке: {me.first_name} (@{me.username})")
    print("Жду входящие сообщения...")
    await client.run_until_disconnected()


if __name__ == "__main__":
    with client:
        try:
            client.loop.run_until_complete(main())
        except KeyboardInterrupt:
            print("\n🛑 Закрыл авто-ответ. До связи, бро!")
