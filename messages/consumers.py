import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import Chat, Message


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"chat_{self.room_name}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_text = data.get("message", "")
            username = data.get("username", "")
            message_type = data.get("message_type", "text")
            
            if message_type == "text" and message_text and username:
                saved_message = await self.save_message(self.room_name, username, message_text)
                
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
            elif message_type in ["image", "file"]:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "chat.message",
                        "message": "",
                        "username": username,
                        "message_id": data.get("message_id"),
                        "message_type": message_type,
                        "url": data.get("url"),
                        "file_name": data.get("file_name", ""),
                    },
                )
        except Exception as e:
            print(f"Error in receive: {e}")

    async def chat_message(self, event):
        response = {
            "message": event["message"],
            "username": event["username"],
            "message_id": event["message_id"],
            "message_type": event.get("message_type", "text"),
        }
        
        if event.get("message_type") in ["image", "file"]:
            response["url"] = event.get("url")
            response["file_name"] = event.get("file_name", "")
        else:
            response["created_at"] = event.get("created_at")
        
        await self.send(text_data=json.dumps(response))

    @database_sync_to_async
    def save_message(self, chat_id, username, message_text):
        try:
            user = User.objects.get(username=username)
            chat = Chat.objects.get(id=chat_id)
            message = Message.objects.create(
                chat=chat,
                sender=user,
                content=message_text,
                message_type='text'
            )
            return message
        except Exception as e:
            print(f"Error saving message: {e}")
            raise
