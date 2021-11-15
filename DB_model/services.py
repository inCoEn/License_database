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

    # @classmethod
    # def _get_increments(cls, server, vendor_name):
    #     """
    #
    #     :param server:
    #     :param vendor_name:
    #     :return:
    #     """