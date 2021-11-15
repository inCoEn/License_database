from django.db import models


class Vendors(models.Model):

    """
    Names of each vendor
    """

    vendor_name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.vendor_name

    class Meta:
        verbose_name_plural = 'Vendors'


class Servers(models.Model):

    """
    License servers with info about state
    and vendor of software installed on it
    """

    server_name = models.CharField(max_length=50)
    port = models.IntegerField()
    state = models.BooleanField()
    vendor = models.ForeignKey(Vendors, on_delete=models.CASCADE)
    description = models.CharField(max_length=500, null=True)

    def __str__(self):
        return self.server_name + f' {self.vendor}'

    class Meta:
        unique_together = ['server_name', 'port']
        verbose_name_plural = 'Servers'


class Increments(models.Model):

    """
    All increment names and amount for each vendor
    """

    inc_name = models.CharField(max_length=200, unique=True)
    vendor = models.ForeignKey(Vendors, on_delete=models.CASCADE)
    total_amount = models.IntegerField()

    def __str__(self):
        return self.inc_name

    class Meta:
        verbose_name_plural = 'Increments'


class Products(models.Model):

    """
    Product name from purchase agreement with his increments
    and vendor
    """

    p_name = models.CharField(max_length=200, unique=True)
    vendor = models.ForeignKey(Vendors, on_delete=models.CASCADE)
    increments = models.ManyToManyField(Increments)
    description = models.CharField(max_length=500, null=True)

    def __str__(self):
        return self.p_name

    class Meta:
        verbose_name_plural = 'Products'


class Software(models.Model):

    """
    Software name with vendor and increments needed to launch
    """

    name = models.CharField(max_length=200, unique=True)
    vendor = models.ForeignKey(Vendors, on_delete=models.CASCADE)
    increments = models.ManyToManyField(Increments)
    description = models.CharField(max_length=500, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Software'


class Departments(models.Model):

    dep_num = models.IntegerField(unique=True)

    def __str__(self):
        return str(self.dep_num)

    class Meta:
        verbose_name_plural = 'Departments'


class Users(models.Model):

    user_name = models.CharField(max_length=100)
    department = models.ForeignKey(Departments, on_delete=models.CASCADE)
    products = models.ManyToManyField(Products)
    software = models.ManyToManyField(Software)

    def __str__(self):
        return f'{self.department}_{self.user_name}'

    class Meta:
        unique_together = ['user_name', 'department']
        verbose_name_plural = 'Users'


class Hosts(models.Model):

    host = models.CharField(max_length=10)
    department = models.ForeignKey(Departments, on_delete=models.CASCADE)

    def __str__(self):
        return self.host

    class Meta:
        unique_together = ['host', 'department']
        verbose_name_plural = 'Hosts'


class MainTable(models.Model):

    """
    The collection of basic data from license server
    """

    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    increment = models.ForeignKey(Increments, on_delete=models.PROTECT)
    user = models.ForeignKey(Users, on_delete=models.PROTECT)
    host = models.ForeignKey(Hosts, on_delete=models.PROTECT)
    amount = models.IntegerField()

    class Meta:
        verbose_name_plural = 'Main Table'
