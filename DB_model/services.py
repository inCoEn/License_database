# Some external functions for working with license servers
import subprocess
from DB_model.models import Servers, Increments, Vendors


class IncrementCache:

    """
    Caching all available increments from all active license servers.
    """

    _CACHE = {}

    def __init__(self):
        self.active_servers = Servers.objects.values_list('server_name',
                                                          'port',
                                                          'vendor_id',
                                                          'vendor_id__vendor_name',
                                                          named=True).filter(state=True)

    @classmethod
    def _get_increments(cls, server, vendor_name):
        """
        Getting increment names and amount for vendor from server
        :param server: str f'{port}@{host}'
        :param vendor_name: str
        :return: None
        """
        lmstat_list = subprocess.getoutput(f'lmutil lmstat -c {server} -a').split('\n')
        vendor_increments = {}

        for line in lmstat_list:
            if line.startswith('Users of') and 'Error' not in line:
                vendor_increments[line.split()[2].replace(':', '')] = line.split()[5]

        if cls._CACHE.get(vendor_name, False):
            cached_vendor_incs = cls._CACHE.get(vendor_name)
            for inc in vendor_increments:
                if inc not in cached_vendor_incs:
                    cls._CACHE[vendor_name][inc] = vendor_increments[inc]
        else:
            cls._CACHE[vendor_name] = vendor_increments

    def update_cache(self):
        """
        Caching all increments from all active servers in DB
        :return: None
        """
        if not self.active_servers:
            return False

        for server in self.active_servers:
            server_name = f'{server.port}@{server.server_name}'
            self._get_increments(server_name, server.veendor_id__vendor_name)

    @classmethod
    def clear_cache(cls):
        cls._CACHE = {}

    @classmethod
    def update_increments_db(cls):
        """
        Updating Increments table in DB
        :return: None
        """
        cached_increments = []
        for vendor in cls._CACHE:

            increments_in_db = Increments.objects.filter(vendor__vendor_name=vendor)\
                .values_list('inc_name', named=True)
            increments_in_db = {item.inc_name: item for item in increments_in_db}

            for inc in cls._CACHE[vendor]:
                if not increments_in_db.get(inc, False):
                    cached_increments.append(Increments(inc_name=inc,
                                                        total_amount=int(cls._CACHE[vendor][inc]),
                                                        vendor=Vendors.objects.get(vendor_name=vendor)))

            if cached_increments:
                Increments.objects.bulk_create(cached_increments)
                print(f'{len(cached_increments)} increments successfully written into DB')
