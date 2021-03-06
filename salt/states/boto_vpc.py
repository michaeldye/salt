# -*- coding: utf-8 -*-
'''
Manage VPCs
=================

.. versionadded:: Beryllium

Create and destroy VPCs. Be aware that this interacts with Amazon's services,
and so may incur charges.

This module uses ``boto``, which can be installed via package, or pip.

This module accepts explicit vpc credentials but can also utilize
IAM roles assigned to the instance through Instance Profiles. Dynamic
credentials are then automatically obtained from AWS API and no further
configuration is necessary. More information available `here
<http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html>`_.

If IAM roles are not used you need to specify them either in a pillar file or
in the minion's config file:

.. code-block:: yaml

    vpc.keyid: GKTADJGHEIQSXMKKRBJ08H
    vpc.key: askdjghsdfjkghWupUjasdflkdfklgjsdfjajkghs

It's also possible to specify ``key``, ``keyid`` and ``region`` via a profile,
either passed in as a dict, or as a string to pull from pillars or minion
config:

.. code-block:: yaml

    myprofile:
        keyid: GKTADJGHEIQSXMKKRBJ08H
        key: askdjghsdfjkghWupUjasdflkdfklgjsdfjajkghs
            region: us-east-1

.. code-block:: yaml

    Ensure VPC exists:
        boto_vpc.present:
            - name: myvpc
            - cidr_block: 10.10.11.0/24
            - dns_hostnames: True
            - region: us-east-1
            - keyid: GKTADJGHEIQSXMKKRBJ08H
            - key: askdjghsdfjkghWupUjasdflkdfklgjsdfjajkghs

    Ensure subnet exists:
        boto_vpc.subnet_present:
            - name: mysubnet
            - vpc_id: vpc-123456
            - cidr_block: 10.0.0.0/16
            - region: us-east-1
            - keyid: GKTADJGHEIQSXMKKRBJ08H
            - key: askdjghsdfjkghWupUjasdflkdfklgjsdfjajkghs

    Ensure internet gateway exists:
        boto_vpc.internet_gateway_present:
            - name: myigw
            - vpc_name: myvpc
            - region: us-east-1
            - keyid: GKTADJGHEIQSXMKKRBJ08H
            - key: askdjghsdfjkghWupUjasdflkdfklgjsdfjajkghs

    Ensure route table exists:
        boto_vpc.route_table_present:
            - name: my_route_table
            - vpc_id: vpc-123456
            - routes:
              - destination_cidr_block: 0.0.0.0/0
                instance_id: i-123456
                interface_id: eni-123456
            - subnets:
              - name: subnet1
              - name: subnet2
            - region: us-east-1
            - keyid: GKTADJGHEIQSXMKKRBJ08H
            - key: askdjghsdfjkghWupUjasdflkdfklgjsdfjajkghs
'''

# Import Python Libs
from __future__ import absolute_import
import logging

# Import Salt Libs
import salt.utils.dictupdate as dictupdate

log = logging.getLogger(__name__)


def __virtual__():
    '''
    Only load if boto is available.
    '''
    return 'boto_vpc' if 'boto_vpc.exists' in __salt__ else False


def present(name, cidr_block, instance_tenancy=None, dns_support=None,
            dns_hostnames=None, tags=None, region=None, key=None, keyid=None,
            profile=None):
    '''
    Ensure VPC exists.

    name
        Name of the VPC.

    cidr_block
        The range of IPs in CIDR format, for example: 10.0.0.0/24. Block
        size must be between /16 and /28 netmask.

    instance_tenancy
        Instances launched in this VPC will be ingle-tenant or dedicated
        hardware.

    dns_support
        Indicates whether the DNS resolution is supported for the VPC.

    dns_hostnames
        Indicates whether the instances launched in the VPC get DNS hostnames.

    tags
        A list of tags.

    region
        Region to connect to.

    key
        Secret key to be used.

    keyid
        Access key to be used.

    profile
        A dict with region, key and keyid, or a pillar key (string) that
        contains a dict with region, key and keyid.
    '''
    ret = {'name': name,
           'result': True,
           'comment': '',
           'changes': {}
           }

    r = __salt__['boto_vpc.exists'](name=name, tags=tags, region=region,
                                    key=key, keyid=keyid, profile=profile)

    if 'error' in r:
        ret['result'] = False
        ret['comment'] = 'Failed to create VPC: {0}.'.format(r['error']['message'])
        return ret

    if not r.get('exists'):
        if __opts__['test']:
            ret['comment'] = 'VPC {0} is set to be created.'.format(name)
            ret['result'] = None
            return ret
        r = __salt__['boto_vpc.create'](cidr_block, instance_tenancy,
                                        name, dns_support, dns_hostnames,
                                        tags, region, key, keyid, profile)
        if not r.get('created'):
            ret['result'] = False
            ret['comment'] = 'Failed to create VPC: {0}.'.format(r['error']['message'])
            return ret
        _describe = __salt__['boto_vpc.describe'](r['id'], region=region, key=key,
                                                  keyid=keyid, profile=profile)
        ret['changes']['old'] = {'vpc': None}
        ret['changes']['new'] = _describe
        ret['comment'] = 'VPC {0} created.'.format(name)
        return ret
    ret['comment'] = 'VPC present.'
    return ret


def absent(name, tags=None, region=None, key=None, keyid=None, profile=None):
    '''
    Ensure VPC with passed properties is absent.

    name
        Name of the VPC.

    tags
        A list of tags. All tags must match.

    region
        Region to connect to.

    key
        Secret key to be used.

    keyid
        Access key to be used.

    profile
        A dict with region, key and keyid, or a pillar key (string) that
        contains a dict with region, key and keyid.
    '''

    ret = {'name': name,
           'result': True,
           'comment': '',
           'changes': {}
           }

    r = __salt__['boto_vpc.get_id'](name=name, tags=tags, region=region,
                                    key=key, keyid=keyid, profile=profile)
    if 'error' in r:
        ret['result'] = False
        ret['comment'] = 'Failed to delete VPC: {0}.'.format(r['error']['message'])
        return ret

    _id = r.get('id')
    if not _id:
        ret['comment'] = '{0} VPC does not exist.'.format(name)
        return ret

    if __opts__['test']:
        ret['comment'] = 'VPC {0} is set to be removed.'.format(name)
        ret['result'] = None
        return ret
    r = __salt__['boto_vpc.delete'](name=name, tags=tags,
                                    region=region, key=key,
                                    keyid=keyid, profile=profile)
    if not r['deleted']:
        ret['result'] = False
        ret['comment'] = 'Failed to delete VPC: {0}.'.format(r['error']['message'])
        return ret
    ret['changes']['old'] = {'vpc': _id}
    ret['changes']['new'] = {'vpc': None}
    ret['comment'] = 'VPC {0} deleted.'.format(name)
    return ret


def subnet_present(name, cidr_block, vpc_name=None, vpc_id=None,
                   availability_zone=None, tags=None, region=None,
                   key=None, keyid=None, profile=None):
    '''
    Ensure a subnet exists.

    name
        Name of the subnet.

    cidr_block
        The range if IPs for the subnet, in CIDR format. For example:
        10.0.0.0/24. Block size must be between /16 and /28 netmask.

    vpc_name
        Name of the VPC in which the subnet should be placed. Either
        vpc_name or vpc_id must be provided.

    vpc_id
        Id of the VPC in which the subnet should be placed. Either vpc_name
        or vpc_id must be provided.

    availability_zone
        AZ in which the subnet should be placed.

    tags
        A list of tags.

    region
        Region to connect to.

    key
        Secret key to be used.

    keyid
        Access key to be used.

    profile
        A dict with region, key and keyid, or a pillar key (string) that
        contains a dict with region, key and keyid.
    '''

    ret = {'name': name,
           'result': True,
           'comment': '',
           'changes': {}
           }

    r = __salt__['boto_vpc.subnet_exists'](subnet_name=name, tags=tags,
                                           region=region, key=key,
                                           keyid=keyid, profile=profile)

    if 'error' in r:
        ret['result'] = False
        ret['comment'] = 'Failed to create subnet: {0}.'.format(r['error']['message'])
        return ret

    if not r.get('exists'):
        if __opts__['test']:
            ret['comment'] = 'Subnet {0} is set to be created.'.format(name)
            ret['result'] = None
            return ret
        r = __salt__['boto_vpc.create_subnet'](subnet_name=name,
                                               cidr_block=cidr_block,
                                               availability_zone=availability_zone,
                                               vpc_name=vpc_name, vpc_id=vpc_id,
                                               tags=tags, region=region,
                                               key=key, keyid=keyid,
                                               profile=profile)
        if not r.get('created'):
            ret['result'] = False
            ret['comment'] = 'Failed to create subnet: {0}'.format(r['error']['message'])
            return ret
        _describe = __salt__['boto_vpc.describe_subnet'](r['id'], region=region, key=key,
                                                         keyid=keyid, profile=profile)
        ret['changes']['old'] = {'subnet': None}
        ret['changes']['new'] = _describe
        ret['comment'] = 'Subnet {0} created.'.format(name)
        return ret
    ret['comment'] = 'Subnet present.'
    return ret


def subnet_absent(name=None, subnet_id=None, region=None, key=None, keyid=None, profile=None):
    '''
    Ensure subnet with passed properties is absent.

    name
        Name of the subnet.

    region
        Region to connect to.

    key
        Secret key to be used.

    keyid
        Access key to be used.

    profile
        A dict with region, key and keyid, or a pillar key (string) that
        contains a dict with region, key and keyid.
    '''

    ret = {'name': name,
           'result': True,
           'comment': '',
           'changes': {}
           }

    r = __salt__['boto_vpc.get_resource_id']('subnet', name=name,
                                             region=region, key=key,
                                             keyid=keyid, profile=profile)
    if 'error' in r:
        ret['result'] = False
        ret['comment'] = 'Failed to delete subnet: {0}.'.format(r['error']['message'])
        return ret

    _id = r.get('id')

    if not _id:
        ret['comment'] = '{0} subnet does not exist.'.format(name)
        return ret

    if __opts__['test']:
        ret['comment'] = 'Subnet {0} ({1}) is set to be removed.'.format(name, r['id'])
        ret['result'] = None
        return ret

    r = __salt__['boto_vpc.delete_subnet'](subnet_name=name,
                                           region=region, key=key,
                                           keyid=keyid, profile=profile)
    if not r.get('deleted'):
        ret['result'] = False
        ret['comment'] = 'Failed to delete subnet: {0}'.format(r['error']['message'])
        return ret

    ret['changes']['old'] = {'subnet': _id}
    ret['changes']['new'] = {'subnet': None}
    ret['comment'] = 'Subnet {0} deleted.'.format(name)
    return ret


def internet_gateway_present(name, vpc_name=None, vpc_id=None,
                             tags=None, region=None, key=None,
                             keyid=None, profile=None):
    '''
    Ensure an internet gateway exists.

    name
        Name of the internet gateway.

    vpc_name
        Name of the VPC to which the internet gateway should be attached.

    vpc_id
        Id of the VPC to which the internet_gateway should be attached.
        Only one of vpc_name or vpc_id may be provided.

    tags
        A list of tags.

    region
        Region to connect to.

    key
        Secret key to be used.

    keyid
        Access key to be used.

    profile
        A dict with region, key and keyid, or a pillar key (string) that
        contains a dict with region, key and keyid.
    '''

    ret = {'name': name,
           'result': True,
           'comment': '',
           'changes': {}
           }

    r = __salt__['boto_vpc.resource_exists']('internet_gateway', name=name,
                                             region=region, key=key,
                                             keyid=keyid, profile=profile)
    if 'error' in r:
        ret['result'] = False
        ret['comment'] = 'Failed to create internet gateway: {0}.'.format(r['error']['message'])
        return ret

    if not r.get('exists'):
        if __opts__['test']:
            ret['comment'] = 'Internet gateway {0} is set to be created.'.format(name)
            ret['result'] = None
            return ret
        r = __salt__['boto_vpc.create_internet_gateway'](internet_gateway_name=name,
                                                         vpc_name=vpc_name, vpc_id=vpc_id,
                                                         tags=tags, region=region,
                                                         key=key, keyid=keyid,
                                                         profile=profile)
        if not r.get('created'):
            ret['result'] = False
            ret['comment'] = 'Failed to create internet gateway: {0}'.format(r['error']['message'])
            return ret

        ret['changes']['old'] = {'internet_gateway': None}
        ret['changes']['new'] = {'internet_gateway': r['id']}
        ret['comment'] = 'Internet gateway {0} created.'.format(name)
        return ret
    ret['comment'] = 'Internet gateway {0} present.'.format(name)
    return ret


def internet_gateway_absent(name, detach=False, region=None,
                            key=None, keyid=None, profile=None):
    '''
    Ensure the named internet gateway is absent.

    name
        Name of the internet gateway.

    detach
        First detach the internet gateway from a VPC, if attached.

    region
        Region to connect to.

    key
        Secret key to be used.

    keyid
        Access key to be used.

    profile
        A dict with region, key and keyid, or a pillar key (string) that
        contains a dict with region, key and keyid.
    '''

    ret = {'name': name,
           'result': True,
           'comment': '',
           'changes': {}
           }

    r = __salt__['boto_vpc.get_resource_id']('internet_gateway', name=name,
                                             region=region, key=key,
                                             keyid=keyid, profile=profile)
    if 'error' in r:
        ret['result'] = False
        ret['comment'] = 'Failed to delete internet gateway: {0}.'.format(r['error']['message'])
        return ret

    igw_id = r['id']
    if not igw_id:
        ret['comment'] = 'Internet gateway {0} does not exist.'.format(name)
        return ret

    if __opts__['test']:
        ret['comment'] = 'Internet gateway {0} is set to be removed.'.format(name)
        ret['result'] = None
        return ret
    r = __salt__['boto_vpc.delete_internet_gateway'](internet_gateway_name=name,
                                                     detach=detach, region=region,
                                                     key=key, keyid=keyid,
                                                     profile=profile)
    if not r.get('deleted'):
        ret['result'] = False
        ret['comment'] = 'Failed to delete internet gateway: {0}.'.format(r['error']['message'])
        return ret
    ret['changes']['old'] = {'internet_gateway': igw_id}
    ret['changes']['new'] = {'internet_gateway': None}
    ret['comment'] = 'Internet gateway {0} deleted.'.format(name)
    return ret


def route_table_present(name, vpc_name=None, vpc_id=None, routes=None,
                        subnet_ids=None, subnet_names=None, tags=None,
                        region=None, key=None, keyid=None, profile=None):
    '''
    Ensure route table with routes exists and is associated to a VPC.


    Example::

    .. code-block:: yaml

        boto_vpc.route_table_present:
            - name: my_route_table
            - vpc_id: vpc-123456
            - routes:
              - destination_cidr_block: 0.0.0.0/0
                instance_id: i-123456
                interface_id: eni-123456
            - subnet_names:
              - subnet1
              - subnet2

    name
        Name of the route table.

    vpc_name
        Name of the VPC with which the route table should be associated.

    vpc_id
        Id of the VPC with which the route table should be associated.
        Either vpc_name or vpc_id must be provided.

    routes
        A list of routes.

    subnet_ids
        A list of subnet ids to associate

    subnet_names
        A list of subnet names to associate

    tags
        A list of tags.

    region
        Region to connect to.

    key
        Secret key to be used.

    keyid
        Access key to be used.

    profile
        A dict with region, key and keyid, or a pillar key (string) that
        contains a dict with region, key and keyid.
    '''
    ret = {'name': name,
           'result': True,
           'comment': '',
           'changes': {}
           }

    _ret = _route_table_present(name=name, vpc_name=vpc_name, vpc_id=vpc_id,
                                tags=tags, region=region, key=key,
                                keyid=keyid, profile=profile)
    ret['changes'] = _ret['changes']
    ret['comment'] = ' '.join([ret['comment'], _ret['comment']])
    if not _ret['result']:
        ret['result'] = _ret['result']
        if ret['result'] is False:
            return ret
    _ret = _routes_present(route_table_name=name, routes=routes, tags=tags, region=region, key=key,
                           keyid=keyid, profile=profile)
    ret['changes'] = dictupdate.update(ret['changes'], _ret['changes'])
    ret['comment'] = ' '.join([ret['comment'], _ret['comment']])
    if not _ret['result']:
        ret['result'] = _ret['result']
        if ret['result'] is False:
            return ret
    _ret = _subnets_present(route_table_name=name, subnet_ids=subnet_ids, subnet_names=subnet_names, tags=tags, region=region, key=key,
                            keyid=keyid, profile=profile)
    ret['changes'] = dictupdate.update(ret['changes'], _ret['changes'])
    ret['comment'] = ' '.join([ret['comment'], _ret['comment']])
    if not _ret['result']:
        ret['result'] = _ret['result']
        if ret['result'] is False:
            return ret
    return ret


def _route_table_present(name, vpc_name=None, vpc_id=None, tags=None, region=None, key=None, keyid=None, profile=None):
    ret = {'name': name,
           'result': True,
           'comment': '',
           'changes': {}
           }

    r = __salt__['boto_vpc.get_resource_id'](resource='route_table', name=name, region=region, key=key, keyid=keyid,
                                             profile=profile)
    if 'error' in r:
        ret['result'] = False
        ret['comment'] = 'Failed to create route table: {0}.'.format(r['error']['message'])
        return ret

    _id = r.get('id')

    if not _id:
        if __opts__['test']:
            msg = 'Route table {0} is set to be created.'.format(name)
            ret['comment'] = msg
            ret['result'] = None
            return ret

        r = __salt__['boto_vpc.create_route_table'](route_table_name=name, vpc_name=vpc_name, vpc_id=vpc_id, tags=tags,
                                                    region=region, key=key, keyid=keyid, profile=profile)
        if not r.get('created'):
            ret['result'] = False
            ret['comment'] = 'Failed to create route table: {0}.'.format(r['error']['message'])
            return ret

        ret['changes']['old'] = {'route_table': None}
        ret['changes']['new'] = {'route_table': r['id']}
        ret['comment'] = 'Route table {0} created.'.format(name)
        return ret
    ret['comment'] = 'Route table {0} ({1}) present.'.format(name, _id)
    return ret


def _routes_present(route_table_name, routes, tags=None, region=None, key=None, keyid=None, profile=None):
    ret = {'name': route_table_name,
           'result': True,
           'comment': '',
           'changes': {}
           }

    route_table = __salt__['boto_vpc.describe_route_table'](route_table_name=route_table_name, tags=tags, region=region,
                                                            key=key, keyid=keyid, profile=profile)
    if 'error' in route_table:
        msg = 'Could not retrieve configuration for route table {0}: {1}`.'.format(route_table_name,
                                                                                   route_table['error']['message'])
        ret['comment'] = msg
        ret['result'] = False
        return ret
    if not routes:
        routes = []
    else:
        route_keys = ['gateway_id', 'instance_id', 'destination_cidr_block', 'interface_id']
        for route in routes:
            for r_key in route_keys:
                route.setdefault(r_key, None)
    to_delete = []
    to_create = []
    for route in routes:
        if dict(route) not in route_table['routes']:
            to_create.append(dict(route))
    for route in route_table['routes']:
        if route not in routes:
            if route['gateway_id'] != 'local':
                to_delete.append(route)
    if to_create or to_delete:
        if __opts__['test']:
            msg = 'Route table {0} set to have routes modified.'.format(route_table_name)
            ret['comment'] = msg
            ret['result'] = None
            return ret
        if to_delete:
            for r in to_delete:
                deleted = __salt__['boto_vpc.delete_route'](route_table['id'], r['destination_cidr_block'], region, key, keyid,
                                                            profile)
                if not deleted:
                    msg = 'Failed to delete route {0} from route table {1}.'.format(r['destination_cidr_block'],
                                                                                    route_table_name)
                    ret['comment'] = msg
                    ret['result'] = False
                ret['comment'] = 'Deleted route {0} from route table {1}.'.format(r['destination_cidr_block'], route_table_name)
        if to_create:
            for r in to_create:
                created = __salt__['boto_vpc.create_route'](route_table_id=route_table['id'], region=region, key=key,
                                                            keyid=keyid, profile=profile, **r)
                if not created:
                    msg = 'Failed to create route {0} in route table {1}.'.format(r['destination_cidr_block'], route_table_name)
                    ret['comment'] = msg
                    ret['result'] = False
                ret['comment'] = 'Created route {0} in route table {1}.'.format(r['destination_cidr_block'], route_table_name)
        ret['changes']['old'] = {'routes': route_table['routes']}
        route = __salt__['boto_vpc.describe_route_table'](route_table_name=route_table_name, tags=tags, region=region, key=key,
                                                          keyid=keyid, profile=profile)
        ret['changes']['new'] = {'routes': route['routes']}
    return ret


def _subnets_present(route_table_name, subnet_ids=None, subnet_names=None, tags=None, region=None, key=None, keyid=None, profile=None):
    ret = {'name': route_table_name,
           'result': True,
           'comment': '',
           'changes': {}
           }

    if not subnet_ids:
        subnet_ids = []

    # Look up subnet ids
    if subnet_names:
        for i in subnet_names:
            r = __salt__['boto_vpc.get_resource_id']('subnet', name=i, region=region,
                                                     key=key, keyid=keyid, profile=profile)

            if 'error' in r:
                msg = 'Error looking up subnet ids: {0}'.format(r['error']['message'])
                ret['comment'] = msg
                ret['result'] = False
                return ret
            if r['id'] is None:
                msg = 'Subnet {0} does not exist.'.format(i)
                ret['comment'] = msg
                ret['result'] = False
                return ret
            subnet_ids.append(r['id'])

    # Describe routing table
    route_table = __salt__['boto_vpc.describe_route_table'](route_table_name=route_table_name, tags=tags, region=region,
                                                            key=key, keyid=keyid, profile=profile)
    if not route_table:
        msg = 'Could not retrieve configuration for route table {0}.'.format(route_table_name)
        ret['comment'] = msg
        ret['result'] = False
        return ret

    assoc_ids = [x['subnet_id'] for x in route_table['associations']]

    to_create = [x for x in subnet_ids if x not in assoc_ids]
    to_delete = [x['id'] for x in route_table['associations'] if x['subnet_id'] not in subnet_ids]

    if to_create or to_delete:
        if __opts__['test']:
            msg = 'Subnet associations for route table {0} set to be modified.'.format(route_table_name)
            ret['comment'] = msg
            ret['result'] = None
            return ret
        if to_delete:
            for r_asc in to_delete:
                r = __salt__['boto_vpc.disassociate_route_table'](r_asc, region, key, keyid, profile)
                if 'error' in r:
                    msg = 'Failed to dissociate {0} from route table {1}: {2}.'.format(r_asc, route_table_name,
                                                                                       r['error']['message'])
                    ret['comment'] = msg
                    ret['result'] = False
                    return ret
                ret['comment'] = 'Dissociated subnet {0} from route table {1}.'.format(r_asc, route_table_name)
        if to_create:
            for sn in to_create:
                r = __salt__['boto_vpc.associate_route_table'](route_table_id=route_table['id'],
                                                               subnet_id=sn,
                                                               region=region, key=key,
                                                               keyid=keyid, profile=profile)
                if 'error' in r:
                    msg = 'Failed to associate subnet {0} with route table {1}: {2}.'.format(sn, route_table_name,
                                                                                             r['error']['message'])
                    ret['comment'] = msg
                    ret['result'] = False
                    return ret
                ret['comment'] = 'Associated subnet {0} with route table {1}.'.format(sn, route_table_name)
        ret['changes']['old'] = {'subnets_associations': route_table['associations']}
        new_sub = __salt__['boto_vpc.describe_route_table'](route_table_name=route_table_name, tags=tags, region=region, key=key,
                                                            keyid=keyid, profile=profile)
        ret['changes']['new'] = {'subnets_associations': new_sub['associations']}
    return ret


def route_table_absent(name, region=None,
                       key=None, keyid=None, profile=None):
    '''
    Ensure the named route table is absent.

    name
        Name of the route table.

    region
        Region to connect to.

    key
        Secret key to be used.

    keyid
        Access key to be used.

    profile
        A dict with region, key and keyid, or a pillar key (string) that
        contains a dict with region, key and keyid.
    '''

    ret = {'name': name,
           'result': True,
           'comment': '',
           'changes': {}
           }

    r = __salt__['boto_vpc.get_resource_id']('route_table', name=name,
                                             region=region, key=key,
                                             keyid=keyid, profile=profile)
    if 'error' in r:
        ret['result'] = False
        ret['comment'] = r['error']['message']
        return ret

    rtbl_id = r['id']

    if not rtbl_id:
        ret['comment'] = 'Route table {0} does not exist.'.format(name)
        return ret

    if __opts__['test']:
        ret['comment'] = 'Route table {0} is set to be removed.'.format(name)
        ret['result'] = None
        return ret

    r = __salt__['boto_vpc.delete_route_table'](route_table_name=name,
                                                region=region,
                                                key=key, keyid=keyid,
                                                profile=profile)
    if 'error' in r:
        ret['result'] = False
        ret['comment'] = 'Failed to delete route table: {0}'.format(r['error']['message'])
        return ret
    ret['changes']['old'] = {'route_table': rtbl_id}
    ret['changes']['new'] = {'route_table': None}
    ret['comment'] = 'Route table {0} deleted.'.format(name)
    return ret
