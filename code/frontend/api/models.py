from tortoise.models import Model
from tortoise import fields

class Player(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=100)

class Game(Model):
    id = fields.IntField(primary_key=True)
    date = fields.DateField()
    player1 = fields.ForeignKeyField('models.Player', related_name='player1')
    player1Score = fields.IntField()
    player2 = fields.ForeignKeyField('models.Player', related_name='player2')
    player2Score = fields.IntField()
    winner = fields.ForeignKeyField('models.Player', related_name='winner', null=True)

    class Meta:
        ordering = ['-date']

class Score(Model):
    id = fields.IntField(primary_key=True)
    player = fields.ForeignKeyField('models.Player', related_name='player')
    game = fields.ForeignKeyField('models.Game', related_name='game')
    score = fields.IntField()
