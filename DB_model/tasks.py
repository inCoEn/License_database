from __future__ import absolute_import, unicode_literals
import os
import datetime
from celery import shared_task
from ast import literal_eval
from django_celery_results.models import TaskResult
from .services import MainTableObjects
from DB_model.models import Increments, Users, Departments, Hosts, MainTable
from License_database.settings import LOG_DIR

ERRORS_LOG = os.path.join(LOG_DIR, 'errors.log')


@shared_task
def save_stats_to_db():
    # List of DB objects for writing
    data_bulk = []

    # Statistics from previous task
    try:
        last_result_id = TaskResult.objects.all().order_by('id').last().id
        last_result = TaskResult.objects.get(id=last_result_id-1)
    except Exception as e:
        last_result = False
        print(e)

    mto = MainTableObjects()
    end_time = datetime.datetime.now()
    end_time = end_time.astimezone(datetime.timezone(datetime.timedelta(hours=4)))
    mto.create_objects()

    current_stats = mto.get_objects()

    if last_result:
        if last_result.status == 'SUCCESS':

            # Convert string from DB to dict
            last_result = literal_eval(last_result.result)
            for vendor in last_result:

                # Fix datetime object
                for item in last_result.get(vendor):
                    dt = datetime.datetime.strptime(item['start'], '%Y-%m-%dT%H:%M:%S%z')
                    dt = dt.astimezone(datetime.timezone(datetime.timedelta(hours=4)))
                    item['start'] = dt

            if current_stats != last_result:
                for vendor in last_result:

                    # If vendor dict not empty
                    if last_result.get(vendor, False):
                        for item in last_result.get(vendor):
                            if item not in current_stats.get(vendor, {}):
                                try:
                                    dep = Departments.objects.get_or_create(dep_num=item['department'])
                                    usr = Users.objects.get_or_create(user_name=item['user'],
                                                                      department=dep[0])
                                    hst = Hosts.objects.get_or_create(host=item['host'],
                                                                      department=dep[0])
                                    inc = Increments.objects.get(inc_name=item['increment'])

                                    db_instance = MainTable(start_date=item['start'],
                                                            end_date=end_time,
                                                            increment=inc,
                                                            user=usr[0],
                                                            host=hst[0],
                                                            amount=item['amount'])
                                except Exception as e:
                                    db_instance = False
                                    with open(ERRORS_LOG, 'a+', encoding='utf-8') as err_log:
                                        err_log.write(str(datetime.datetime.now())+'\n')
                                        err_log.write(str(e)+'\n')
                                        err_log.write('-'*30+'\n')
                                if db_instance:
                                    data_bulk.append(db_instance)
                    if data_bulk:
                        MainTable.objects.bulk_create(data_bulk)
                        print(f'{len(data_bulk)} objects written')
    return current_stats
