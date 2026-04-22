from django.db import models
from django.contrib.auth.models import User


class Conversation(models.Model):
    user1 = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="conversations_initiator"
    )
    user2 = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="conversations_receiver"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = [["user1", "user2"]]

    def __str__(self):
        return f"{self.user1.username} <-> {self.user2.username}"

    @staticmethod
    def get_or_create_conversation(user1, user2):
        """Get or create a conversation between two users, ensuring consistent ordering."""
        if user1.id > user2.id:
            user1, user2 = user2, user1

        conversation, _ = Conversation.objects.get_or_create(user1=user1, user2=user2)
        return conversation


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return f"{self.sender.username}: {self.text[:50]}"
