#!/usr/bin/env python

from lxml import etree
from cpstwinning.securitymanager import Predicates, RuleTypes


class AmlParser(object):

    def __init__(self, aml_path):
        self.aml_path = aml_path
        self.plcs = []
        self.hmis = []
        self.motors = []
        self.switches = []
        self.security_rules = {}
        self.run()

    def run(self):

        tree = etree.parse(self.aml_path)
        root = tree.getroot()

        def get_val_text(a):
            text_list = a.xpath('./Value/text()')
            return text_list[0] if len(text_list) else None

        def get_id_attr(el):
            return el.attrib['ID']

        def get_plc_modbus_map(el):
            # address: plc_var_name
            # address: Modbus address
            # plc_var_name: variable name in PLC code (must be converted to idx of var array later on)
            mb_map = {
                'di': {},
                'co': {},
                'hr': {},
                'ir': {}
            }

            def get_plc_mb_map_links(plc_el):
                links = []
                for link in plc_el.xpath(
                        './InternalElement[@RefBaseSystemUnitPath=\"LogicalDeviceSystemUnitClassLib/IOController'
                        '\"]/InternalElement/RoleRequirements['
                        '@RefBaseRoleClassPath=\"ModbusRoleClassLib/ModbusMap\"]/..//InternalElement/InternalLink'):
                    links.append({'name': get_name_attr(link), 'a': link.attrib['RefPartnerSideA'],
                                  'b': link.attrib['RefPartnerSideB']})
                return links

            def get_plc_var_name_by_mb_ref(links, ref):
                partner_ref = get_partner_ref(links, ref)
                partner_ref_id = partner_ref[partner_ref.find("{") + 1:partner_ref.find("}")]
                partner_ref_name = partner_ref.split(":")[1]
                value = el.xpath(
                    './InternalElement[@ID=\"{}\"]/ExternalInterface[@Name=\"{}\" and '
                    '@RefBaseClassPath=\"AutomationMLInterfaceClassLibLogics/VariableInterface\"]/Attribute['
                    '@Name=\"refURI\"]/Value/text()'.format(
                        partner_ref_id, partner_ref_name))
                if len(value):
                    return value[0].split('#')[1]
                else:
                    raise RuntimeError('Could not retrieve PLC var name via Modbus map.')

            def get_partner_ref(links, ref):
                for link in links:
                    a = 'a'
                    b = 'b'
                    for _ in range(2):
                        if link[a] == ref:
                            return link[b]
                        # Swap sides
                        a, b = b, a

            def get_mapping(table, links, table_name):
                res = {}
                tbl = table.xpath(
                    './InternalElement/RoleRequirements[@RefBaseRoleClassPath=\"ModbusRoleClassLib/ModbusSlave/Tables'
                    '/{}\"]/..'.format(
                        table_name))
                if len(tbl):
                    ref_id = get_id_attr(tbl[0])
                    for ch in tbl[0].iter("ExternalInterface"):
                        name = get_name_attr(ch)
                        mb_ref = '{{{}}}:{}'.format(ref_id, name)
                        plc_var_name = get_plc_var_name_by_mb_ref(links, mb_ref)
                        res[int(name)] = plc_var_name
                return res

            mb_links = get_plc_mb_map_links(el)
            mb_tables = el.xpath(
                './InternalElement/RoleRequirements[@RefBaseRoleClassPath=\"ProgramBlocksRoleClassLib/Main'
                '\"]/../InternalElement/RoleRequirements['
                '@RefBaseRoleClassPath=\"ModbusRoleClassLib/ModbusTCPSlave\"]/../InternalElement/RoleRequirements['
                '@RefBaseRoleClassPath=\"ModbusRoleClassLib/ModbusSlave/Tables\"]/..')
            if len(mb_tables):
                mb_map['co'] = get_mapping(mb_tables[0], mb_links, 'DiscreteOutputCoils')
                mb_map['di'] = get_mapping(mb_tables[0], mb_links, 'DiscreteInputContacts')
                mb_map['hr'] = get_mapping(mb_tables[0], mb_links, 'AnalogOutputHoldingRegisters')
                mb_map['ir'] = get_mapping(mb_tables[0], mb_links, 'AnalogInputRegisters')
            else:
                raise RuntimeError('Could not retrieve Modbus tables.')
            return mb_map

        def get_plc_st_path(el):
            text_list = el.xpath(
                './InternalElement/RoleRequirements[@RefBaseRoleClassPath=\"ProgramBlocksRoleClassLib/Main'
                '\"]/../ExternalInterface[@RefBaseClassPath=\"AutomationMLInterfaceClassLib/AutomationMLBaseInterface'
                '/ExternalDataConnector/PLCopenXMLInterface\"]/Attribute[@Name=\"refSTURI\"]/Value/text()')
            return text_list[0] if len(text_list) else None

        def get_name_attr(el):
            return el.attrib['Name']

        def get_network_config(el):
            network_config = {'mac': None, 'ip': None, 'netmask': None}
            for a in el.xpath(
                    './InternalElement/ExternalInterface['
                    '@RefBaseClassPath=\"CommunicationInterfaceClassLib/CommunicationPhysicalSocket\"]//Attribute'):
                if a.attrib['Name'] == 'mac':
                    network_config['mac'] = get_val_text(a)
                elif a.attrib['Name'] == 'ip':
                    network_config['ip'] = get_val_text(a)
                elif a.attrib['Name'] == 'netmask':
                    network_config['netmask'] = get_val_text(a)

            return network_config

        def get_plc_var_map(el, motor_variables):

            def get_plc_var_map_links(link_el):
                links = []
                for var_map_i_link in link_el.xpath(
                        './InternalElement[@RefBaseSystemUnitPath=\"CPSTwinningSystemUnitClassLib/PLCVarMap'
                        '\"]//InternalLink'):
                    links.append({'name': get_name_attr(var_map_i_link), 'a': var_map_i_link.attrib['RefPartnerSideA'],
                                  'b': var_map_i_link.attrib['RefPartnerSideB']})
                return links

            plc_var_map = {}
            plc_var_links = get_plc_var_map_links(el)
            for link in plc_var_links:
                side = 'a'
                plc_var_name = None
                motor_var_idx = None
                for _ in range(2):
                    ref_partner = link[side]
                    ref_partner_id = ref_partner[ref_partner.find("{") + 1:ref_partner.find("}")]
                    ref_partner_name = ref_partner.split(":")[1]
                    ext_intf = root.xpath(
                        './/InternalElement[@ID=\"{}\"]/ExternalInterface[@Name=\"{}\"]'.format(ref_partner_id,
                                                                                                ref_partner_name))
                    if len(ext_intf):
                        base_class_path = ext_intf[0].get('RefBaseClassPath')
                        # Check if ref partner is PLC variable
                        if base_class_path == 'AutomationMLInterfaceClassLibLogics/VariableInterface':
                            value = ext_intf[0].xpath('./Attribute[@Name=\"refURI\"]/Value/text()')
                            if len(value):
                                plc_var_name = value[0].split('#')[1]
                        else:
                            plc_var_map_ie = ext_intf[0].getparent()
                            base_system_unit_path = plc_var_map_ie.get('RefBaseSystemUnitPath')
                            if base_system_unit_path == 'CPSTwinningSystemUnitClassLib/PLCVarMap':
                                motor_var_name = get_name_attr(ext_intf[0])
                                motor_var_idx = motor_variables.index(
                                    filter(lambda n: n.get('name') == motor_var_name, motor_variables)[0])
                    side = 'b'
                if plc_var_name is not None and motor_var_idx is not None:
                    plc_var_map[plc_var_name.upper()] = motor_var_idx

            return plc_var_map

        def get_motor_vars(el):
            motor_variables = []
            vars_ext_intf = el.xpath(
                './InternalElement[@RefBaseSystemUnitPath=\"CPSTwinningSystemUnitClassLib/PLCVarMap'
                '\"]//ExternalInterface')
            for v in vars_ext_intf:
                name = get_name_attr(v)
                type_txt = v.xpath('./Attribute[@Name=\"type\"]/Value/text()')
                if len(type_txt):
                    t = type_txt[0]
                    if t == 'int':
                        init_val = 0
                    elif t == 'boolean':
                        init_val = False
                    else:
                        raise RuntimeError('Unsupported type found ({}).'.format(t))

                    motor_variables.append({'name': name, 'value': init_val})

            return motor_variables

        def get_plc_name_for_motor(el):

            def get_physical_network_partner_ref(motor_control_reference):
                link = root.xpath('./InstanceHierarchy/InternalElement/RoleRequirements['
                                  '@RefBaseRoleClassPath=\"CommunicationRoleClassLib/PhysicalNetwork'
                                  '\"]/../InternalElement/RoleRequirements['
                                  '@RefBaseRoleClassPath=\"CommunicationRoleClassLib/PhysicalNetwork'
                                  '/PhysicalConnection\"]/../InternalLink[@RefPartnerSideA=\"{}\" or '
                                  '@RefPartnerSideB=\"{}\"]'
                                  .format(motor_control_reference, motor_control_reference))
                if len(link):
                    li = link[0]
                    if li.get('RefPartnerSideA') == el:
                        return li.get('RefPartnerSideB')
                    else:
                        return li.get('RefPartnerSideA')

            def get_name_by_ref(ref):
                ref_id = ref[ref.find("{") + 1:ref.find("}")]
                tmp_ie_plc = root.xpath('./InstanceHierarchy/InternalElement/RoleRequirements['
                                        '@RefBaseRoleClassPath=\"AutomationMLCSRoleClassLib/ControlEquipment/Controller'
                                        '/PLC\"]/' +
                                        '../InternalElement[@ID=\"{}\"]/..'.format(ref_id))
                if len(tmp_ie_plc):
                    return get_name_attr(tmp_ie_plc[0])

            # First get MotorControl ref
            ie_motor_control = el.xpath(
                './InternalElement/RoleRequirements[@RefBaseRoleClassPath=\"ConveyorComponentsRoleClassLib/Motor'
                '/MotorControl\"]/..')
            if len(ie_motor_control):
                motor_control_id = get_id_attr(ie_motor_control[0])
                ext_intf = ie_motor_control[0].xpath('./ExternalInterface')
                if len(ext_intf):
                    channel_name = get_name_attr(ext_intf[0])
                    motor_control_ref = '{{{}}}:{}'.format(motor_control_id, channel_name)
                    # Retrieve partner_ref from Physical Network
                    partner_ref = get_physical_network_partner_ref(motor_control_ref)
                    # Get Name of PLC
                    return get_name_by_ref(partner_ref)

        def get_switch_links(switch_el):

            def get_switch_endpoints_refs(el):
                endpoints = el.xpath(
                    './InternalElement/ExternalInterface['
                    '@RefBaseClassPath=\"CommunicationInterfaceClassLib/SwitchCommunicationPhysicalSocket\"]')
                if len(endpoints):
                    e0 = endpoints[0]
                    portlist = e0.getparent()
                    portlist_id = get_id_attr(portlist)
                    return list(map(lambda x: '{{{}}}:{}'.format(portlist_id, get_name_attr(x)), endpoints))

            def get_name_by_ref(ref_el):
                tmp_id = ref_el[ref.find("{") + 1:ref_el.find("}")]
                ie = root.xpath('./InstanceHierarchy/InternalElement/InternalElement[@ID=\"{}\"]/..'.format(tmp_id))
                if len(ie):
                    return get_name_attr(ie[0])

            endpoint_refs = get_switch_endpoints_refs(switch_el)
            internal_links = root.xpath('./InstanceHierarchy/InternalElement' +
                                        '/RoleRequirements[@RefBaseRoleClassPath=\"CommunicationRoleClassLib'
                                        '/PhysicalNetwork\"]/../InternalElement/InternalLink')
            partner_refs = []
            side_a = 'RefPartnerSideA'
            side_b = 'RefPartnerSideB'
            for internal_link in internal_links:
                if internal_link.get(side_a) in endpoint_refs:
                    partner_refs.append(internal_link.get(side_b))
                elif internal_link.get(side_b) in endpoint_refs:
                    partner_refs.append(internal_link.get(side_a))

            switch_links = []
            for ref in partner_refs:
                switch_links.append(get_name_by_ref(ref))

            return switch_links

        def retrieve_var_constraints(el, plc_name):
            attrs_w_constraints = el.xpath(
                './InternalElement/RoleRequirements[@RefBaseRoleClassPath=\"ProgramBlocksRoleClassLib/Main\"]' +
                '/../ExternalInterface[@RefBaseClassPath=\"AutomationMLInterfaceClassLibLogics/VariableInterface\"]' +
                '/Attribute[@Name=\"refURI\"]/Constraint/..')
            constraints = []
            for attr in attrs_w_constraints:
                value_text = attr.xpath('./Value/text()')
                if len(value_text):
                    value = value_text[0]
                    var_name = value.split('#')[1]
                    predicate_els = attr.xpath('./Constraint/OrdinalScaledType/RequiredMaxValue')
                    if len(predicate_els):
                        predicate_el = predicate_els[0]
                        if predicate_el.tag == Predicates().MAXVAL:
                            constraints.append(
                                {
                                    'plc_name': plc_name,
                                    'var_name': var_name,
                                    'predicate': Predicates().MAXVAL,
                                    'value': int(predicate_el.text)
                                }
                            )
                        else:
                            print "WARNING: Skipped unsupported predicate '{}'.\n".format(predicate_el.tag)

            return constraints

        # def get_hmi_vars(el):
        #
        #    def get_plc_var_partner_ref(hmi_var_ref):
        #        i_links = root.xpath(
        #            './InstanceHierarchy/InternalElement/RoleRequirements['
        #            '@RefBaseRoleClassPath=\"CommunicationRoleClassLib/LogicalNetwork\"]' +
        #            '/../InternalElement[@RefBaseSystemUnitPath=\"LogicalConnectionSystemUnitClassLib'
        #            '/LogicalConnection\"]/InternalElement/RoleRequirements['
        #            '@RefBaseRoleClassPath=\"ModbusRoleClassLib/ModbusTCPDataPacket\"]' +
        #            '/../InternalLink[@RefPartnerSideA=\"{}\" or @RefPartnerSideB=\"{}\"]' \
        #            .format(hmi_var_ref, hmi_var_ref))
        #        if len(i_links):
        #            i_link = i_links[0]
        #            side_a = 'RefPartnerSideA'
        #            side_b = 'RefPartnerSideB'
        #            if i_link.attrib[side_a] == hmi_var_ref:
        #                return i_link.attrib[side_b]
        #            else:
        #                return i_link.attrib[side_a]
        #
        #    hmi_vars = []
        #    # Retrieve HMI variables specified in HMI IE
        #    ext_intf_hmi_vars = el.xpath(
        #        './InternalElement[@RefBaseSystemUnitPath=\"LogicalDeviceSystemUnitClassLib/HMI\"]' +
        #        '/ExternalInterface[@RefBaseClassPath=\"LogicalDeviceInterfaceClassLib/HMIVariableInterface\"]')
        #    if len(ext_intf_hmi_vars):
        #        # TODO: Parse name + type for init val
        #        parent_id = get_id_attr(ext_intf_hmi_vars[0].getparent())
        #        for ei in ext_intf_hmi_vars:
        #            hmi_var_ref = '{{{}}}:{}'.format(parent_id, get_name_attr(ei))
        #            # Reference of PLC var stored in Program
        #            plc_var_partner_ref = get_plc_var_partner_ref(hmi_var_ref)
        #            # TODO:
        #            # Retrieve Modbus map
        #            # Parse refs from Modbus map
        #            # Get addr + reg (Modbus)
        #

        # Init security rules
        self.security_rules[RuleTypes().VARCONSTRAINT] = []
        self.security_rules[RuleTypes().VARLINKCONSTRAINT] = []

        for ie_hmi in root.xpath(
                './InstanceHierarchy/InternalElement/RoleRequirements['
                '@RefBaseRoleClassPath=\"AutomationMLExtendedRoleClassLib/HMI\"]/..'):
            hmi = {'name': get_name_attr(ie_hmi), 'network': get_network_config(ie_hmi)}
            # TODO: Call HMI vars method
            # get_hmi_vars(ie_hmi)
            self.hmis.append(hmi)

        for ie_plc in root.xpath(
                './InstanceHierarchy/InternalElement/RoleRequirements['
                '@RefBaseRoleClassPath=\"AutomationMLCSRoleClassLib/ControlEquipment/Controller/PLC\"]/..'):
            plc = {'name': get_name_attr(ie_plc), 'network': get_network_config(ie_plc)}
            st_path = get_plc_st_path(ie_plc)
            if st_path:
                plc['st_path'] = st_path
            else:
                raise RuntimeError('Could not retrieve path of ST code.')
            plc['mb_map'] = get_plc_modbus_map(ie_plc)

            self.plcs.append(plc)

            self.security_rules[RuleTypes().VARCONSTRAINT].extend(retrieve_var_constraints(ie_plc, plc['name']))

        for ie_motor in root.xpath(
                './InstanceHierarchy/InternalElement/RoleRequirements['
                '@RefBaseRoleClassPath=\"ConveyorComponentsRoleClassLib/Motor\"]/..'):
            motor_vars = get_motor_vars(ie_motor)
            motor = {
                'name': get_name_attr(ie_motor),
                'vars': motor_vars,
                'plc_var_map': get_plc_var_map(ie_motor, motor_vars),
                'plc_name': get_plc_name_for_motor(ie_motor)
            }
            self.motors.append(motor)

        for ie_switch in root.xpath(
                './InstanceHierarchy/InternalElement/RoleRequirements['
                '@RefBaseRoleClassPath=\"NetworkComponentsRoleClassLib/Switch\"]/..'):
            switch = {'name': get_name_attr(ie_switch), 'links': get_switch_links(ie_switch)}
            self.switches.append(switch)

        var_link_constraints = []
        # Variable Link Constraints
        for ie_var_link_constraints in root.xpath(
                './InstanceHierarchy/InternalElement/RoleRequirements['
                '@RefBaseRoleClassPath=\"ConstraintRoleClassLib/VariableLinkConstraintRoleClass\"]/..'):
            constraint = {}
            operator = ie_var_link_constraints.xpath('./Attribute[@Name=\"operator\"]/Value/text()')
            if len(operator) == 1:
                if operator[0] == Predicates().EQUALS:
                    constraint['predicate'] = Predicates().EQUALS
            i_link = ie_var_link_constraints.xpath('./InternalLink')
            if len(i_link) == 1:
                ref_a = i_link[0].attrib['RefPartnerSideA']
                ref_b = i_link[0].attrib['RefPartnerSideB']
                a_var_name = ref_a.split(':')[1]
                b_var_name = ref_b.split(':')[1]
                a_id = ref_a[ref_a.find("{") + 1:ref_a.find("}")]
                b_id = ref_b[ref_b.find("{") + 1:ref_b.find("}")]
                a_name_l = root.xpath('./InstanceHierarchy//InternalElement[@ID=\"{}\"]/..'.format(a_id))
                b_name_l = root.xpath('./InstanceHierarchy//InternalElement[@ID=\"{}\"]/..'.format(b_id))
                if len(a_name_l) and len(b_name_l):
                    a_name = a_name_l[0].attrib['Name']
                    constraint['a'] = {a_name: a_var_name}
                    b_name = b_name_l[0].attrib['Name']
                    constraint['b'] = {b_name: b_var_name}

                    var_link_constraints.append(constraint)

        self.security_rules[RuleTypes().VARLINKCONSTRAINT].extend(var_link_constraints)
