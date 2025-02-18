# coding: utf-8

import re
import argparse
import inspect
from modules.utils import yellow, print_error

# - - - - - - - - - - - - - - - - - - - - - - - - - -
# Get command line arguments
# - - - - - - - - - - - - - - - - - - - - - - - - - -
def get_cmd_arguments():

        parser=argparse.ArgumentParser()

        parser.add_argument("-auth", 
                            default="", 
                            dest="user_auth",
                            help="Force an authentication method : cs (cloudshell), cf (config file), ip (instance principals"
                            )
        parser.add_argument("-config_file", 
                            default="~/.oci/config", 
                            dest="config_file_path",
                            help="Path to your OCI config file, default: ~/.oci/config"
                            )
        parser.add_argument("-profile", 
                            default="DEFAULT", 
                            dest="config_profile",
                            help="Config file section to use, default: DEFAULT"
                            )
        parser.add_argument('-su', 
                            action='store_true',
                            default=False, 
                            dest='su',
                            help='If you have tenancy-level admin rights search for compute instances from the root compartment'
                            )
        parser.add_argument("-comp",
                            default="",
                            dest="comp",
                            help="Compartment ocid to analyze, default is root compartment"
                            )
        parser.add_argument("-region",
                            default="",
                            dest="target_region",
                            help="Region name to analyze, e.g. 'eu-frankfurt-1' or 'all_regions', default is home region"
                            )
        parser.add_argument("-update",
                            action="store_true",
                            default=False,
                            dest="update",
                            help="Force update to IMDSv2"
                            )
        parser.add_argument("-stop",
                            action="store_true",
                            default=False,
                            dest="stop",
                            help="Force stop IMDSv1 instances"
                            )
        return parser.parse_args()

def get_missing_arguments(args):

    try:
        if not args.user_auth:
            while True:
                auth_select=input(yellow("\n\nPick auth method: CS (CloudShell), CF (Config File), IP (Instance Principals): ")).strip().lower()
                if auth_select in ["cs", "cf", "ip"]:
                    break

            if auth_select == "ip":
                args.user_auth="ip"
            elif auth_select == "cs":
                args.user_auth="cs"
            else:
                args.user_auth="cf"        
                args.config_file_path=input(yellow("\nEnter the path to your OCI config file or press Enter to use '~/.oci/config': ")).strip().lower()
                args.config_profile=input(yellow("\nEnter the Config profile to use or press Enter to use 'DEFAULT': ")).strip().upper()
                
                args.config_file_path="~/.oci/config" if not args.config_file_path else args.config_file_path
                args.config_profile="DEFAULT" if not args.config_profile else args.config_profile

        if not args.target_region :
            # OCI Region name format pattern
            region_pattern=r"^[a-zA-Z]{2}-[a-zA-Z]{1,20}-[1-9]$"
            while True:
                region_select=input(yellow("\nEnter a Region name (e.g., eu-frankfurt-1 or all_regions) or press Enter to use your home region: ")).strip().lower()
                if not region_select:
                    # If input is empty, will use home region
                    args.target_region=""
                    break
                elif region_select == "all_regions" or re.match(region_pattern, region_select):
                    args.target_region=region_select
                    break

        return args
    
    except Exception as e:
        function_name=inspect.currentframe().f_code.co_name
        if hasattr(e, "code") and hasattr(e, "message"):
            print_error(f"An error occurred in -- {function_name} --:", e.code, e.message)
        else:
            print_error(f"An error occurred in -- {function_name} --:", e)
        return None
