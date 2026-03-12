from tortoise import fields, models

class User(models.Model):
    telegram_id = fields.BigIntField(pk=True)
    full_name = fields.CharField(max_length=255)
    username = fields.CharField(max_length=255, null=True)
    balance = fields.IntField(default=0)
    referral_count = fields.IntField(default=0)
    referred_by = fields.BigIntField(null=True)
    is_banned = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    is_ref_rewarded = fields.BooleanField(default=False)

class Vote(models.Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="votes")
    phone_number = fields.CharField(max_length=20, unique=True)
    screenshot_id = fields.CharField(max_length=255)
    status = fields.CharField(max_length=20, default="pending") # pending, approved, rejected
    created_at = fields.DatetimeField(auto_now_add=True)

class Withdrawal(models.Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="withdrawals")
    system_name = fields.CharField(max_length=50)
    wallet_number = fields.CharField(max_length=50)
    amount = fields.IntField()
    status = fields.CharField(max_length=20, default="pending") # pending, paid, rejected
    created_at = fields.DatetimeField(auto_now_add=True)

class Setting(models.Model):
    key = fields.CharField(max_length=50, pk=True)
    value = fields.CharField(max_length=255)
    
class Channel(models.Model):
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=100)
    is_mandatory = fields.BooleanField(default=True) # True: Majburiy obuna, False: To'lovlar kanali

class PaymentSystem(models.Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=50)
    
class OBVote(models.Model):
    id = fields.IntField(pk=True)
    initiative_id = fields.CharField(max_length=255)
    phone_number = fields.CharField(max_length=20)
    vote_date = fields.DatetimeField() # Ovoz berilgan vaqt
    created_at = fields.DatetimeField(auto_now_add=True) # Bazaga yozilgan vaqt

    class Meta: # type: ignore
        table = "ob_votes"
        # Bitta raqam bir vaqtda 2 marta ovoz berolmaydi, shu orqali dublikatlarni oldini olamiz
        unique_together = (("phone_number", "vote_date", "initiative_id"),)
        ordering = ["-vote_date"]
        
