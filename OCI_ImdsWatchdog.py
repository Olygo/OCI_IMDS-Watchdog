# coding: utf-8

# - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# name: OCI_ImdsWatchdog.py
#
# Author: Florian Bonneville
# Version: 1.0.0 - February 18th, 2025
#
# Disclaimer: 
# This script is an independent tool developed by 
# Florian Bonneville and is not affiliated with or 
# supported by Oracle. It is provided as-is and without 
# any warranty or official endorsement from Oracle
#
# - - - - - - - - - - - - - - - - - - - - - - - - - - - -
version="1.0.0"

import os
import oci
import time
import logging
from datetime import datetime
from modules.search import set_search_query, search_instances
from modules.utils import *
from modules.identity import *
from modules.workrequests import monitor_workrequest
from modules.arguments import get_cmd_arguments, get_missing_arguments

# - - - - - - - - - - - - - - - - - - - - - - - - - -
# Set logging file and format
# - - - - - - - - - - - - - - - - - - - - - - - - - -
now=datetime.now().strftime("%Y-%m-%d_%H-%M")
log_file=f'imds-report_{now}.log'

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# - - - - - - - - - - - - - - - - - - - - - - - - - -
# Clear shell screen
# - - - - - - - - - - - - - - - - - - - - - - - - - -
clear()

# - - - - - - - - - - - - - - - - - - - - - - - - - -
# Load command line arguments
# - - - - - - - - - - - - - - - - - - - - - - - - - -
args=get_cmd_arguments()
args=get_missing_arguments(args)

args_dict = vars(args)

for arg, value in args_dict.items():
    logging.info(f"{arg}: {value}")

# - - - - - - - - - - - - - - - - - - - - - - - - - -
# Init OCI authentication
# - - - - - - - - - - - - - - - - - - - - - - - - - -
config, signer, tenancy, auth_name, details=init_authentication(
     args.user_auth, 
     args.config_file_path, 
     args.config_profile
     )

# - - - - - - - - - - - - - - - - - - - - - - - - - -
# Init oci service client
# - - - - - - - - - - - - - - - - - - - - - - - - - -
identity_client=oci.identity.IdentityClient(
     config=config, 
     signer=signer)

tenancy_id=config["tenancy"]

# - - - - - - - - - - - - - - - - - - - - - - - - - -
# Set target compartment
# - - - - - - - - - - - - - - - - - - - - - - - - - -
top_level_compartment_id = set_user_compartment(
    identity_client, 
    args.su, 
    args.comp, 
    tenancy_id
    )

# - - - - - - - - - - - - - - - - - - - - - - - - - -
# Clear shell screen in case of authentication errors
# - - - - - - - - - - - - - - - - - - - - - - - - - -
clear()

# - - - - - - - - - - - - - - - - - - - - - - - - - -
# Start printing script info
# - - - - - - - - - - - - - - - - - - - - - - - - - -
script_path=os.path.abspath(__file__)
script_name=(os.path.basename(script_path))[:-3]
script_version=version
print(green(f"\n{'*'*94:94}"))
print_info(green, "Script", "started", script_name)
print_info(green, "Script", "version", script_version)
print_info(green, "Login", "success", auth_name)
print_info(green, "Login", "profile", details)
print_info(green, "Tenancy", tenancy.name, f"home region: {tenancy.home_region_key}")

# - - - - - - - - - - - - - - - - - - - - - - - - - -
# Set target region(s)
# - - - - - - - - - - - - - - - - - - - - - - - - - -
regions_to_analyze=get_region_subscription_list(
     identity_client,
     tenancy_id,
     args.target_region
     )
regions_validated, region_errors=validate_region_connectivity(
     regions_to_analyze,
     config,
     signer
     )
home_region=get_home_region(
     identity_client, 
     tenancy_id
     )

# - - - - - - - - - - - - - - - - - - - - - - - - - -
# Fetch parent compartment and child compartments
# - - - - - - - - - - - - - - - - - - - - - - - - - -
my_compartments=get_compartment_list(identity_client, top_level_compartment_id)
compartment_name=identity_client.get_compartment(top_level_compartment_id).data.name

# - - - - - - - - - - - - - - - - - - - - - - - - - -
# End print script info
# - - - - - - - - - - - - - - - - - - - - - - - - - -
print_info(green, "Region(#)", "selected", len(regions_validated))
print_info(green, "Compartment", "name", compartment_name)
print_info(green, "Compartment(s)", "quantity", len(my_compartments))
if args.update:
    print_info(green, "Force", "IMDSv2", "Yes")
else:
    print_info(green, "Force", "IMDSv2", "No")
if args.stop:
    print_info(green, "Force", "Stop", "Yes")
else:
    print_info(green, "Force", "Stop", "No")
print(green(f"{'*'*94:94}\n"))

# - - - - - - - - - - - - - - - - - - - - - - - - -² -
# Start analysis
# - - - - - - - - - - - - - - - - - - - - - - - - - -

# Force the first config in home region if multiples regions
config["region"]=home_region.region_name
identity_client=oci.identity.IdentityClient(config=config, signer=signer)
core_client=oci.core.ComputeClient(config=config, signer=signer)

# - - - - - - - - - - - - - - - - - - - - - - - - - -
# Start script duration counter
# - - - - - - - - - - - - - - - - - - - - - - - - - -
analysis_start=time.perf_counter()

# Set the root compartment ID
root_compartment_id = config["tenancy"]

for region in regions_validated:

    print(f"\nProcessing: {region.region_name}")
    # Print hearders
    print(green(f"{'REGION':<25}{'COMPARTMENT':<30}{'INSTANCE':<30}{'STATE':<10}{'IMDS V2':<8}\n"))

    # Init IMDS count
    IMDSv1=0
    IMDSv2=0

    config["region"]=region.region_name

    identity_client=oci.identity.IdentityClient(config=config, signer=signer)
    core_client=oci.core.ComputeClient(config=config, signer=signer)
    WorkRequest_client=oci.work_requests.WorkRequestClient(config=config, signer=signer)

    query=set_search_query(args, my_compartments, logging)
    instances=search_instances(config, signer, query, logging)

    for instance in instances.data:
        try:
            instance=core_client.get_instance(instance.identifier).data
            compartment=identity_client.get_compartment(instance.compartment_id).data
            Imds_State="True" if instance.instance_options.are_legacy_imds_endpoints_disabled else "False"

            # If IMDS is set to false (=IMDSv1)
            if not instance.instance_options.are_legacy_imds_endpoints_disabled:
                IMDSv1 += 1 
                logging.info(f"{compartment.name} {instance.display_name} {Imds_State}")
                print(yellow(f"{region.region_name[:20]:<25}{compartment.name[:25]:<30}{instance.display_name[:25]:<30}{instance.lifecycle_state[:8]:<10}{Imds_State:<8}"))

                # Stop IMDSv1 instances if '-stop' option used
                if args.stop:
                    core_client.instance_action(instance.id, action='SOFTSTOP')
                    monitor_workrequest(WorkRequest_client, instance)
                    instance=core_client.get_instance(instance_id=instance.id).data
                    Imds_State="True" if instance.instance_options.are_legacy_imds_endpoints_disabled else "False"
                    logging.info(f"{compartment.name} {instance.display_name} has been {instance.lifecycle_state}")
                    print(f"{region.region_name[:20]:<25}{compartment.name[:25]:<30}{instance.display_name[:25]:<30}{instance.lifecycle_state[:8]:<10}{Imds_State:<8}")

                # Change to IMDSv2 if '-update' option used
                if args.update:
                    update_instance_response = core_client.update_instance(
                        instance_id=instance.id,
                        update_instance_details=oci.core.models.UpdateInstanceDetails(
                            instance_options=oci.core.models.InstanceOptions(
                                are_legacy_imds_endpoints_disabled=True)
                                ))
                    monitor_workrequest(WorkRequest_client, instance)
                    instance=core_client.get_instance(instance_id=instance.id).data
                    Imds_State="True" if instance.instance_options.are_legacy_imds_endpoints_disabled else "False"
                    logging.info(f"{compartment.name} {instance.display_name} {Imds_State}")
                    print(f"{region.region_name[:20]:<25}{compartment.name[:25]:<30}{instance.display_name[:25]:<30}{instance.lifecycle_state[:8]:<10}{Imds_State:<8}")
                    IMDSv1 -= 1
                    IMDSv2 += 1
            else:
                logging.info(f"{compartment.name} {instance.display_name} {Imds_State}")
                print(f"{region.region_name[:20]:<25}{compartment.name[:25]:<30}{instance.display_name[:25]:<30}{instance.lifecycle_state[:8]:<10}{Imds_State:<8}")
                IMDSv2 += 1
        except:
            print(yellow(f"{region.region_name[:20]:<25}{compartment.name[:25]:<30}{instance.display_name[:25]:<30}{'GET_ERROR':<10}{'ERROR':<8}"))
            pass

    logging.info(f"IMDSv1 instances in {region.region_name}: {IMDSv1}")
    logging.info(f"IMDSv2 instances in {region.region_name}: {IMDSv2}")
    print(yellow(f"\nIMDSv1 instances in {region.region_name}: {IMDSv1}"))
    print(yellow(f"IMDSv2 instances in {region.region_name}: {IMDSv2}\n"))

print(" "*60)

# - - - - - - - - - - - - - - - - - - - - - - - - - -
# End script duration counter
# - - - - - - - - - - - - - - - - - - - - - - - - - -
analysis_end=time.perf_counter()
execution_time=analysis_end - analysis_start
logging.info(f"Execution time: {format_duration(execution_time)}")
print(green(f"\nExecution time: {format_duration(execution_time)}"))
print(green(f"IMDS report: ./{log_file}\n"))