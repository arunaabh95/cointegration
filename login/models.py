from django.db import models

# Create your models here.

class User(models.Model):
    id = models.AutoField(primary_key=True)
    fname = models.CharField(max_length=50)
    lname = models.CharField(max_length=50)
    email = models.EmailField(max_length=254, unique=True)
    password = models.CharField(max_length=50)

    def get_full_name(self):
        return self.fname + " " + self.lname
    
    def get_first_name(self):
        return self.fname
    
    def get_email(self):
        return self.email

class Pair(models.Model):
    stock1 = models.CharField(max_length=50)
    stock2 = models.CharField(max_length=50)
    sector = models.CharField(max_length=50)
    score = models.FloatField()

    class Meta:
        unique_together = ('stock1', 'stock2')

    @property
    def get_pairs(self):
        return self._meta.unique_together
    
    def get_score(self):
        return self.score

class Transaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    pair = models.ForeignKey(Pair, on_delete=models.CASCADE, db_column='unique_key_id')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, default=None)
    db_table='transaction'

    # might not need this
    def get_user(self):
        return str(self.user) 
    
    # might not need this
    def get_stock_pair(self):
        return self.pair
    
    def get_start_time(self):
        return self.end_time 
    
    def get_end_time(self):
        return self.end_time
    
