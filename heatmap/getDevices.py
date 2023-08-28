from heatmap.pingTasks import ping
from celery import Celery, group, shared_task
import time
from datetime import datetime
from celery.result import allow_join_result
import settings
import logging
import psycopg2
from netmiko import ConnectHandler
import re
from publicfunction import get_bearer_token, get_vault_secret
from config import dbserver, NETWORK_ENV


retry_kwargs = {"max_retries": 3,
                "retry_backoff": False}
# retry in 5 minutes


@shared_task(bind=True, default_retry_delay=5*60, retry_kwargs=retry_kwargs)
def get_devices(self):
    try:
        logger = logging.getLogger('tasks')

        exec_Time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        token = get_bearer_token()

        RouterUsername = get_vault_secret(
            token, "RouterUsername", "DataBaseName")
        RouterPassword = get_vault_secret(
            token, "RouterPassword", "DataBaseName")

        server = dbserver[NETWORK_ENV]
        database = "DataBaseName"
        DbUsername = get_vault_secret(
            token, "DbUsername", "DataBaseName")
        DbPassword = get_vault_secret(
            token, "DbPassword", "DataBaseName")

        # Connect to DB
        conn = psycopg2.connect(
            host=server, dbname=database, user=DbUsername, password=DbPassword)
        conn.autocommit = True

        # Create DB cursor
        cursor = conn.cursor()

        # exec SQL to query device list
        cursor.execute(
            'SELECT Query')

        # get device from database
        result = cursor.fetchall()

        device_dic = {}

        for row in result:
            device = row[0]
            ip = row[1]
            device_dic[device] = ip

        logger.info(device_dic)
        logger.info('--------------------------------------------------')
        dev_string = "[" + "],[".join(device_dic.keys()) + "]"
        logger.info(f'Device Query from database {dev_string}')

        logger.info('--------------------------------------------------')
        ip_string = "[" + "],[".join(device_dic.values()) + "]"
        logger.info(f'Ip Query from database {ip_string}')

        logger.info('--------------------------------------------------')
        logger.info('Check device connection')
        # Use the appropriate network driver to connect to the device:

        # driver = napalm.get_network_driver("ios")
        failed_connect_devices = []
        for device in list(device_dic.keys()):
            device_ip = device_dic[device]
            ios_device = {
                "device_type": "cisco_ios",
                "ip": device_ip,
                "username": RouterUsername,
                "password": RouterPassword,
                "fast_cli": False,
                "timeout": 60
            }

            try:
                with ConnectHandler(**ios_device) as devices:
                    output = devices.send_command(
                        f"ping {device_ip}", cmd_verify=False, expect_string=r".*")
                    cursor.execute(
                    f"call Stored Procedure ('{device}','{exec_Time}');")
            except Exception as e:
                logger.error(
                    f'Unable to connect to {device}. Will remove from list')
                logger.error(e)
                # countries.pop("device")
                failed_connect_devices.append(device)
                del device_dic[device]
                cursor.execute(
                    f"call Stored Procedure ('{device}','{exec_Time}');")

        if len(device_dic) > 0:
            logger.info('--------------------------------------------------')
            valid_dev_string = "[" + "],[".join(device_dic.keys()) + "]"
            logger.info(f'Valid Device {valid_dev_string}')

            logger.info('--------------------------------------------------')
            logger.info('call storeprocedure move real data to history')
            logger.info('start time: ' +
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            # call storeprocedure move real data to history
            cursor.execute("call StoredProcedure")

            device_list = list(device_dic.keys())
            ip_list = list(device_dic.values())
            # update failed_connect_devices pingresult to 999
            failed_records = []
            sql_batch = 500
            for faileddevice in failed_connect_devices:
                for device2 in device_list:
                    insert_string = f"call StoredProcedure ('{faileddevice}','{device2}',999,'{exec_Time}')"
                    failed_records.append(insert_string)
                    if (len(failed_records) == sql_batch):
                        failed_tmp_records = "; ".join(failed_records)
                        logger.info(failed_tmp_records)
                        cursor.execute(failed_tmp_records)
                        failed_records = []
            for device1 in device_list:
                for faileddevice in failed_connect_devices:
                    insert_string = f"call StoredProcedure ('{device1}','{faileddevice}',999,'{exec_Time}')"
                    failed_records.append(insert_string)
                    if (len(failed_records) == sql_batch):
                        failed_tmp_records = "; ".join(failed_records)
                        logger.info(failed_tmp_records)
                        cursor.execute(failed_tmp_records)
                        failed_records = []
            for faileddevice1 in failed_connect_devices:
                for faileddevice2 in failed_connect_devices:
                    insert_string = f"call StoredProcedure ('{faileddevice1}','{faileddevice2}',999,'{exec_Time}')"
                    failed_records.append(insert_string)
                    if (len(failed_records) == sql_batch):
                        failed_tmp_records = "; ".join(failed_records)
                        logger.info(failed_tmp_records)
                        cursor.execute(failed_tmp_records)
                        failed_records = []

            if (len(failed_records) >= 1):
                failed_tmp_records = "; ".join(failed_records)
                cursor.execute(failed_tmp_records)
                failed_records = []

            # call sub tasks
            tasks = group(ping.s(device, device_list, ip_list, exec_Time, RouterUsername, RouterPassword, DbUsername, DbPassword)
                          for device in device_dic.keys())
            result_group = tasks.apply_async(queue='QueueName')
            successful = result_group.successful()
            while not result_group.ready():
                time.sleep(5)
                logger.info('waiting 5 seconds for subtask to complete....')
            # get sub tasks data
            with allow_join_result():
                logger.info('Result data from subtasks: ')
                results = result_group.get()
            logger.info('Results from subtasks: ')
            logger.info(results)

            # sort by device,device2
            sorted_results = []
            for result in results:
                sorted_results += sorted(result,
                                         key=lambda x: (x['device'], x['device2']))
            insert_records = []
            sql_batch = 500

            for subresult in sorted_results:
                device1, device2, avg_response = subresult[
                    'device'], subresult['device2'], subresult['avg_response']
                insert_string = f"call StoredProcedure ('{device1}','{device2}',{avg_response},'{exec_Time}')"
                insert_records.append(insert_string)
                if (len(insert_records) == sql_batch):
                    insert_tmp_records = "; ".join(insert_records)
                    logger.info(insert_tmp_records)
                    cursor.execute(insert_tmp_records)
                    insert_records = []

            if (len(insert_records) >= 1):
                insert_tmp_records = "; ".join(insert_records)
                cursor.execute(insert_tmp_records)
        else:
            logger.error('Unable to connect all the devices')

        # Previously data was all saved to temp table, so now moving data from temp to the real one. Reason for doing this is that there is an interval between cleaning up the table and getting the new data.
        # If PowerBI report refresh dataset during the time that the table is empty then it shows nothing on the report.
        cursor.execute("call StoredProcedure()")

        # Convert device name so that it can fit in PowerBI heatmap
        #cursor.execute("call udsp_pingresult_deviceconversion()")

        # delete data from heatmapdevice_pinghistory that already exists for an year
        cursor.execute("call StoredProcedure()")
        logger.info('end time: ' +
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        # close cursor
        cursor.close()
        # close db conn
        conn.close()
    except Exception as ex:
        logger.error('Exception: ')
        logger.error(ex)
