#!/usr/bin/env python
# -*- encoding: utf-8 -*-

# Galera Monitoring
# Copyright (C) 2015 Tobias Urdin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

STATE_OK = 0
STATE_WARNING = 1
STATE_CRITICAL = 2
STATE_UNKNOWN = 3

import sys

try:
    import argparse
except ImportError:
    print 'You must have the argparse package installed.'
    sys.exit(STATE_UNKNOWN)

try:
    import pymysql
except ImportError:
    print 'You must have the pymysql package installed.'
    sys.exit(STATE_CRITICAL)

parser = argparse.ArgumentParser(description='Check Galera')

parser.add_argument('--host', metavar='localhost',
                    type=str, required=False,
                    default='localhost',
                    help='MySQL host')
parser.add_argument('--port', metavar='3306', type=int, required=False,
                    default='3306', help='MySQL port')
parser.add_argument('--username', metavar='username', type=str, required=True,
                    help='MySQL username')
parser.add_argument('--password', metavar='password', type=str, required=True,
                    help='MySQL password')
parser.add_argument('--warning', type=str, required=False,
                    help='Warning for amount of nodes in cluster')
parser.add_argument('--critical', type=str, required=False,
                    help='Critical for amount of nodes in cluster')
parser.add_argument('--fcp', type=float, required=False,
                    default=0.1,
                    help='Max value for the wsrep_flow_control_paused variable')
parser.add_argument('--primary', action='store_true', required=False,
                    help='Alarm if this node is not primary')

args = parser.parse_args()

try:
    conn = pymysql.connect(host=args.host, port=args.port, user=args.username, passwd=args.password, db='mysql', cursorclass=pymysql.cursors.DictCursor)
except Exception, e:
    print 'CRITICAL: Failed to connect to MySQL'
    sys.exit(STATE_CRITICAL)

try:
    cursor = conn.cursor()
except Exception, e:
    print 'CRITICAL: Failed to grab MySQL cursor'
    sys.exit(STATE_CRITICAL)

def get_value_from_query(cursor, query):
    if not cursor:
        return None

    cursor.execute(query)
    result = cursor.fetchone()

    if not result:
        return None

    if 'Value' not in result:
        return None

    return result['Value']

def get_cluster_size(cursor):
    return get_value_from_query(cursor, "SHOW STATUS LIKE 'wsrep_cluster_size'")

def get_cluster_status(cursor):
    return get_value_from_query(cursor, "SHOW STATUS LIKE 'wsrep_cluster_status'")

def get_flow_control_paused(cursor):
    return get_value_from_query(cursor, "SHOW STATUS LIKE 'wsrep_flow_control_paused'")

def get_ready(cursor):
    return get_value_from_query(cursor, "SHOW STATUS LIKE 'wsrep_ready'")

def get_connected(cursor):
    return get_value_from_query(cursor, "SHOW STATUS LIKE 'wsrep_connected'")

def get_local_state_comment(cursor):
    return get_value_from_query(cursor, "SHOW STATUS LIKE 'wsrep_local_state_comment'")

if __name__ == '__main__':
    flow_control_paused = get_flow_control_paused(cursor)

    if flow_control_paused is None:
        print 'CRITICAL: Failed to get wsrep_flow_control_paused'
        sys.exit(STATE_CRITICAL)

    if float(flow_control_paused) > float(args.fcp):
        print 'CRITICAL: wsrep_flow_control_paused is above limit %s' % (str(args.fcp))
        sys.exit(STATE_CRITICAL)

    if args.primary:
        cluster_status = get_cluster_status(cursor)

        if cluster_status is None:
            print 'CRITICAL: Failed to get wsrep_cluster_status'
            sys.exit(STATE_CRITICAL)

        if cluster_status != 'Primary':
            print 'CRITICAL: Node is not primary (%s)' % (cluster_status)
            sys.exit(STATE_CRITICAL)

    ready = get_ready(cursor)

    if ready is None:
        print 'CRITICAL: Failed to get wsrep_ready'
        sys.exit(STATE_CRITICAL)

    if ready != 'ON':
        print 'CRITICAL: Node is not ready (%s)' % (ready)
        sys.exit(STATE_CRITICAL)

    connected = get_connected(cursor)

    if connected is None:
        print 'CRITICAL: Failed to get wsrep_connected'
        sys.exit(STATE_CRITICAL)

    if connected != 'ON':
        print 'CRITICAL: Node is not connected (%s)' % (connected)
        sys.exit(STATE_CRITICAL)

    local_state_comment = get_local_state_comment(cursor)

    if local_state_comment is None:
        print 'CRITICAL: Faield to get wsrep_local_state_comment'
        sys.exit(STATE_CRITICAL)

    if local_state_comment != 'Synced':
        print 'CRITICAL: Node is not synced (%s)' % (local_state_comment)
        sys.exit(STATE_CRITICAL)

    cluster_size = get_cluster_size(cursor)

    if cluster_size is None:
        print 'CRITICAL: Failed to get wsrep_cluster_size'
        sys.exit(STATE_CRITICAL)

    if args.critical is not None:
        if int(cluster_size) < int(args.critical):
                print 'CRITICAL: Nodes in cluster is %s' % (cluster_size)
                sys.exit(STATE_CRITICAL)

    if args.warning is not None:
        if int(cluster_size) < int(args.warning):
                print 'WARNING: Nodes in cluster is %s' % (cluster_size)
                sys.exit(STATE_WARNING)

    print 'OK: Nodes in cluster is %s' % (cluster_size)
    sys.exit(STATE_OK)
