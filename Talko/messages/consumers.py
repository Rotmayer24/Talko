import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

from .models import Chat, Message

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get("user")
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"chat_{self.room_name}"

        if self.user is None or not self.user.is_authenticated:
            await self.close(code=4001)
            return

        if not await self.is_member(self.room_name, self.user.id):
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except (json.JSONDecodeError, TypeError):
            return

        username = self.user.username
        message_type = data.get("message_type", "text")

        if message_type == "delete":
            message_id = data.get("message_id")
            if message_id:
                deleted = await self.delete_message(
                    self.room_name, self.user.id, message_id
                )
                if deleted:
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            "type": "chat.delete",
                            "message_id": message_id,
                            "username": username,
                        },
                    )
            return

        if message_type == "text":
            message_text = (data.get("message") or "").strip()
            if not message_text:
                return

            saved_message = await self.save_message(self.room_name, message_text)
            if saved_message is None:
                return

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat.message",
                    "message": message_text,
                    "username": username,
                    "message_id": saved_message.id,
                    "created_at": saved_message.created_at.isoformat(),
                    "message_type": "text",
                },
            )
        elif message_type in ("image", "file", "video"):
            message_id = data.get("message_id")
            payload = await self.get_attachment_payload(
                self.room_name, self.user.id, message_id
            )
            if payload is None:
                return

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat.message",
                    "message": "",
                    "username": username,
                    "message_id": message_id,
                    "message_type": message_type,
                    "url": payload["url"],
                    "file_name": payload["file_name"],
                },
            )

    async def chat_message(self, event):
        response = {
            "message": event["message"],
            "username": event["username"],
            "message_id": event["message_id"],
            "message_type": event.get("message_type", "text"),
        }

        if event.get("message_type") in ("image", "file", "video"):
            response["url"] = event.get("url")
            response["file_name"] = event.get("file_name", "")
        else:
            response["created_at"] = event.get("created_at")

        await self.send(text_data=json.dumps(response))

    async def chat_delete(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "delete",
                    "message_id": event["message_id"],
                    "username": event["username"],
                }
            )
        )

    @database_sync_to_async
    def is_member(self, chat_id, user_id):
        return Chat.objects.filter(id=chat_id, users__id=user_id).exists()

    @database_sync_to_async
    def save_message(self, chat_id, message_text):
        try:
            chat = Chat.objects.get(id=chat_id, users__id=self.user.id)
        except Chat.DoesNotExist:
            return None

        return Message.objects.create(
            chat=chat,
            sender=self.user,
            content=message_text,
            message_type="text",
        )

    @database_sync_to_async
    def get_attachment_payload(self, chat_id, user_id, message_id):
        if not message_id:
            return None
        try:
            message = Message.objects.get(
                id=message_id,
                chat_id=chat_id,
                sender_id=user_id,
            )
        except Message.DoesNotExist:
            return None

        if message.message_type == "image" and message.image:
            url = message.image.url
        elif message.message_type == "file" and message.file:
            url = message.file.url
        elif message.message_type == "video" and message.video:
            url = message.video.url
        else:
            return None

        return {"url": url, "file_name": message.file_name}

    @database_sync_to_async
    def delete_message(self, chat_id, user_id, message_id):
        try:
            message = Message.objects.get(
                id=message_id,
                chat_id=chat_id,
                sender_id=user_id,
            )
        except Message.DoesNotExist:
            return False
        message.deleted = True
        message.content = ""
        message.save()
        return True
