from celery import shared_task
import napalm
import settings
import logging
import psycopg2
from netmiko import ConnectHandler
import re
from napalm.base.exceptions import ConnectionClosedException
from publicfunction import get_bearer_token, get_vault_secret
from config import dbserver, NETWORK_ENV


retry_kwargs = {"max_retries": 3, "retry_backoff": False}
# retry in 5 minutes


@shared_task(bind=True, default_retry_delay=5*60, retry_kwargs=retry_kwargs)
def ping(self, device, device_list, ip_list, exec_Time, RouterUsername, RouterPassword, DbUsername, DbPassword):
    logger = logging.getLogger('tasks')
    # driver = napalm.get_network_driver("ios")

    server = dbserver[NETWORK_ENV]
    database = "DataBaseName"

    logger.info('Initiating tests from {}'.format(device))
    device_index = device_list.index(device)
    device_ip = ip_list[device_index]
    ios_device = {
        "device_type": "cisco_ios",
        "ip": device_ip,
        "username": RouterUsername,
        "password": RouterPassword,
        "fast_cli": False,
        "timeout": 60
    }

    results = []
    try:
        with ConnectHandler(**ios_device) as iosdevice:
            for device2 in device_list:
                try:

                    device2_index = device_list.index(device2)
                    device2_ip = ip_list[device2_index]
                    output = iosdevice.send_command(
                        f"ping {device2_ip}", cmd_verify=False, expect_string=r"round-trip")
                    logger.info(output)
                    if 'Success' in output:
                        parts = output.split('=')
                        if len(parts) > 0:
                            ping_str = parts[1]
                            print(parts[1])

                            avg_ping = re.findall(r'\d+', ping_str)[1]
                            if avg_ping:
                                ping_result = {'device': device, 'device2': device2,
                                               'avg_response': avg_ping}
                                results.append(ping_result)

                            else:
                                logger.error(
                                    f'Failed to ping {device2} from {device} (1)')
                                ping_result = {'device': device, 'device2': device2,
                                               'avg_response': 999}
                                results.append(ping_result)
                        else:
                            logger.error(
                                f'Failed to ping {device2} from {device} (2)')
                            ping_result = {'device': device, 'device2': device2,
                                           'avg_response': 999}
                            results.append(ping_result)
                    elif '0.00% packet loss' in output:
                        parts = output.split('/')
                        if len(parts) > 0:
                            avg_ping = parts[3]
                            if avg_ping:
                                ping_result = {'device': device, 'device2': device2,
                                               'avg_response': avg_ping}
                                results.append(ping_result)

                            else:
                                logger.error(
                                    f'Failed to ping {device2} from {device} (1)')
                                ping_result = {'device': device, 'device2': device2,
                                               'avg_response': 999}
                                results.append(ping_result)
                        else:
                            logger.error(
                                f'Failed to ping {device2} from {device} (2)')
                            ping_result = {'device': device, 'device2': device2,
                                           'avg_response': 999}
                            results.append(ping_result)
                    else:
                        logger.error(f'Failed to ping {device2} from {device} (3)')
                        ping_result = {'device': device, 'device2': device2,
                                       'avg_response': 999}
                        results.append(ping_result)

                except Exception as e:
                    logger.error(f'Failed to ping {device2} from {device} (4)')
                    logger.error(e)
                    ping_result = {'device': device, 'device2': device2,
                                   'avg_response': 999}
                    results.append(ping_result)
    except Exception as e:
        logger.error(f'Unable to connect to device {device} from pingtask. (5)')
        logger.error(e)
        for device2 in device_list:
            ping_result = {'device': device, 'device2': device2,
                           'avg_response': 999}
        results.append(ping_result)
        # Connect to DB
        try:
            conn = psycopg2.connect(
                host=server, dbname=database, user=DbUsername, password=DbPassword)
            conn.autocommit = True
            # Create DB cursor
            cursor = conn.cursor()
            cursor.execute(
                f"call Stored Procedure ('{device}','{exec_Time}');")

            # close cursor
            cursor.close()
            # close db conn
            conn.close()
        except Exception as e:
            logger.error(
                f'Unable to connect to database from pingtask. {e} (6)')
    return tuple(results)
