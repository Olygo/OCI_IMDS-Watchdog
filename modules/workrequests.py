# coding: utf-8

import oci
import time
import inspect
from modules.utils import print_error, yellow
   
def get_wr_details(WorkRequest_client, workrequest_id):

    try:
        wrDetails=WorkRequest_client.get_work_request(workrequest_id).data
        return wrDetails
    except Exception as e:
        function_name=inspect.currentframe().f_code.co_name
        if hasattr(e, "code") and hasattr(e, "message"):
            print_error(f"An error occurred in -- {function_name} --:", e.code, e.message)
        else:
            print_error(f"An error occurred in -- {function_name} --:", e)
        return None

def list_wr_errors(WorkRequest_client, workrequest_id):

    try:
        wrErrors=WorkRequest_client.list_work_request_errors(workrequest_id).data
        return wrErrors
    except Exception as e:
        function_name=inspect.currentframe().f_code.co_name
        if hasattr(e, "code") and hasattr(e, "message"):
            print_error(f"An error occurred in -- {function_name} --:", e.code, e.message)
        else:
            print_error(f"An error occurred in -- {function_name} --:", e)
        return None
    
def list_wr_logs(WorkRequest_client, workrequest_id):

    try:
        log_limit=5
        page_size=1
        wrLogs=oci.pagination.list_call_get_up_to_limit(WorkRequest_client.list_work_request_logs, log_limit, page_size, workrequest_id).data
        return wrLogs
    except Exception as e:
        function_name=inspect.currentframe().f_code.co_name
        if hasattr(e, "code") and hasattr(e, "message"):
            print_error(f"An error occurred in -- {function_name} --:", e.code, e.message)
        else:
            print_error(f"An error occurred in -- {function_name} --:", e)
        return None

def monitor_workrequest(WorkRequest_client, instance):

    workrequests=WorkRequest_client.list_work_requests(compartment_id=instance.compartment_id, resource_id=instance.id).data

    # fetch work request logs during 600 seconds
    for _ in range(600):
        try:
            wrDetails=get_wr_details(WorkRequest_client, workrequests[0].id)
            wrLogs=list_wr_logs(WorkRequest_client, workrequests[0].id)
            wrErrors=list_wr_errors(WorkRequest_client, workrequests[0].id)
            wrLog=wrLogs[0].message if wrLogs else None
            wrError=wrErrors[0].message if wrErrors else None
            wrLog=wrError or wrLog

            print(yellow(f"\r          => WorkRequest: {wrDetails.operation_type} - {wrDetails.resources[0].action_type} - {wrDetails.percent_complete}% => {wrLog}"),end="\r "*150, flush=True)

            time.sleep(1)
            
            if wrDetails.percent_complete == 100.0:
                print("\r",end=" "*150+"\r", flush=True)
                #break
                return True

            if wrDetails.status == "FAILED":
                print_error(
                    "Work request failed:", 
                    wrDetails.status
                    )
                #break
                return False

        except Exception as e:
            function_name=inspect.currentframe().f_code.co_name
            if hasattr(e, "code") and hasattr(e, "message"):
                print_error(f"An error occurred in -- {function_name} --:", e.code, e.message)
            else:
                print_error(f"An error occurred in -- {function_name} --:", e)
            #break
            return False
