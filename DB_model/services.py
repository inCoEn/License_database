# Some external functions for working with license servers
import datetime
import subprocess
import threading
import re
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


class MainTableObject:
    """
    Creating objects for writing into DB
    """

    # Objects dict {vendor: [{increment, start, user, host, amount}, ]}
    _objects = {}
    # Strings dict for _prepare_server_lines {vendor: [log]}
    _lines = {}

    def __init__(self):
        self.active_servers = Servers.objects.filter(state=True).values_list('server_name',
                                                                             'port',
                                                                             'vendor__vendor_name',
                                                                             named=True)

    @classmethod
    def _get_lm_stat(cls, server):
        """
        Getting stats from license server as a list of strings
        :param server: django.db.models.utils.Row
        :return: None
        """

        server_log = subprocess.run(['lmutil', 'lmstat', '-c', f'{server.port}@{server.server_name}', '-a'],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
        if not server_log.stderr and server_log.stdout:
            server_log = server_log.stdout.decode('utf-8').split('\n')
            cls._lines[server.vendor__vendor_name] = server_log

    def _get_statistics(self):
        """
        Getting stats in multi treads
        :return: None
        """

        # With threads ~1.9s
        # Without threads ~3.9s

        threads = []

        for server in self.active_servers:
            thread = threading.Thread(target=self._get_lm_stat, args=(server,))
            threads.append(thread)
            thread.start()
        for t in threads:
            t.join()

    @classmethod
    def _prepare_server_lines(cls, vendor):
        """
        Processing strings from _lines and writing them to _objects
        :param vendor: str
        :return: None
        """

        increment, start, user, department, host, count = (None, None, None, None, None, None)
        server_lines = []

        for line in cls._lines[vendor]:
            if line:
                # Detecting string with increment in format "increment"
                # If vendor is MSC, increment detecting from current line
                # In other cases increment detecting from previous lines
                if line.split()[0].startswith('\"'):
                    increment = line.split()[0][1:-1]
                elif vendor == 'MSC':
                    if re.search('CAMPUS:\S+', line):
                        increment = re.search('CAMPUS:\S+', line).group().replace('CAMPUS:', '')
                start = re.search('\w+ \d{1,2}/\d{1,2} \d{1,2}:\d{1,2}', line)
                if start:
                    start = start.group() + '' + str(datetime.datetime.now().year)
                    start = datetime.datetime.strptime(start, '%a %m/%d %H:%M %Y')
                    start = start.astimezone(datetime.timezone(datetime.timedelta(hours=4)))
                dep_user = re.search('\d{4}_\w+', line)
                if dep_user:
                    user = dep_user.group().split('_')[1]
                    department = dep_user.group().split()[0]
                elif 'SYSTEM' in line:
                    user = 'SYSTEM'
                    department = 9999

                # For local hosts
                pc = re.search('\d{4}-\d{1,2}', line)
                if pc:
                    host = pc.group()

                # For clusters
                elif re.search('SABF\d{2}-*\d{0,2}', line):
                    host = re.search('SABF\d{2}-*\d{0,2}', line).group()
                elif re.search('sabo\d{2}', line):
                    host = re.search('sabo\d{2}', line).group()
                elif re.search('SABO\d{2}', line):
                    host = re.search('SABO\d{2}', line).group()

                # For virtual desktops
                elif re.search('vd\d+\w+-\d+', line):
                    host = re.search('vd\d+\w+-\d+', line).group()
                amount = re.search('\d{1,3} licenses', line)
                if amount:
                    amount = amount.group().replace('licenses', '')
                else:
                    amount = 1

                log_line = {'increment': increment,
                            'start': start,
                            'user': user,
                            'department': department,
                            'host': host,
                            'amount': amount}
                is_valid = []
                for key in log_line:
                    is_valid.append(log_line.get(key, None))
                if None not in is_valid:
                    server_lines.append(log_line)
        cls._objects[vendor] = server_lines

    def create_objects(self):

        self._get_statistics()

        # With treads or without threads anyway ~1.5s

        # threads = []
        #
        # for server in self.active_servers:
        #     thread = threading.Thread(target=self._prepare_server_lines, args=(server.vendor__vendor_name,))
        #     threads.append(thread)
        #     thread.start()
        # for t in threads:
        #     t.join()

        for server in self.active_servers:
            self._prepare_server_lines(server.vendor__vendor_name)

    @classmethod
    def get_objects(cls):
        return cls._objects
