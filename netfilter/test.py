# -*- coding: utf-8 -*-
#
# python-netfilter - Python modules for manipulating netfilter rules
# Copyright (C) 2007-2012 Bolloré Telecom
# Copyright (C) 2013 Jeremy Lainé
# See AUTHORS file for a full list of contributors.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import unittest
import logging

import netfilter.table
from netfilter.rule import Rule,Target,Match
import netfilter.parser

iptables_data = """# Generated by iptables-save v1.4.8 on Wed Sep 19 11:07:12 2012
*filter
:INPUT DROP [556:75796]
:FORWARD DROP [204:11510]
:OUTPUT ACCEPT [1884:214582]
:firewall_forward_filter - [0:0]
:firewall_input_filter - [0:0]
[7480114:987402857] -A INPUT -j firewall_input_filter 
[759445591:598252573508] -A FORWARD -j firewall_forward_filter 
[3323456:179228827] -A firewall_forward_filter -p tcp -m state --state NEW -m multiport --dports 22,80,443 -j ULOG --ulog-prefix "FORWARD" --ulog-cprange 100 --ulog-qthreshold 10 
[112148:127429710] -A firewall_input_filter -i lo -j ACCEPT 
[4830789:639904091] -A firewall_input_filter -m state --state RELATED,ESTABLISHED -j ACCEPT 
[7964:372765] -A firewall_input_filter -p icmp -j ACCEPT 
[215:12972] -A firewall_input_filter -p tcp -m state --state NEW -m multiport --dports 22 -j ULOG --ulog-prefix "INPUT" --ulog-cprange 100 --ulog-qthreshold 10 
[215:12972] -A firewall_input_filter -p tcp -m multiport --dports 22 -j ACCEPT 
[935044:68004850] -A firewall_input_filter -i eth1.161 -p udp -m multiport --dports 53,67 -j ACCEPT 
[216374:11435810] -A firewall_input_filter -i eth1.161 -p tcp -m multiport --dports 8089,8090 -j ACCEPT 
[141:9420] -A firewall_input_filter -i eth1.161 -p tcp -m multiport --dports 5222,7777,8080 -j ACCEPT 
[652708:44603726] -A firewall_input_filter -i eth1.171 -p udp -m multiport --dports 53,67 -j ACCEPT 
[82187:4331634] -A firewall_input_filter -i eth1.171 -p tcp -m multiport --dports 8089,8090 -j ACCEPT 
[125:9171] -A firewall_input_filter -i eth1.171 -p tcp -m multiport --dports 5222,7777,8080 -j ACCEPT 
COMMIT
# Completed on Wed Sep 19 11:07:13 2012
"""

class ParserTestCase(unittest.TestCase):
    def testSplitWords(self):
        self.assertEqual(netfilter.parser.split_words('a b c'),
            ['a', 'b', 'c'])
        self.assertEqual(netfilter.parser.split_words('a\tb  c'),
            ['a', 'b', 'c'])

    def testSplitWordsQuoted(self):
        line = 'a "some text" b'
        self.assertEqual(netfilter.parser.split_words(line),
            ['a', 'some text', 'b'])

    def testParseChains(self):
        chains = netfilter.parser.parse_chains(iptables_data)

        self.assertEquals(chains.keys(), ['INPUT', 'FORWARD', 'OUTPUT', 'firewall_forward_filter', 'firewall_input_filter'])

        self.assertEquals(chains['INPUT']['policy'], 'DROP')
        self.assertEquals(chains['INPUT']['bytes'], 75796)
        self.assertEquals(chains['INPUT']['packets'], 556)

        self.assertEquals(chains['FORWARD']['policy'], 'DROP')
        self.assertEquals(chains['FORWARD']['bytes'], 11510)
        self.assertEquals(chains['FORWARD']['packets'], 204)

        self.assertEquals(chains['OUTPUT']['policy'], 'ACCEPT')
        self.assertEquals(chains['OUTPUT']['bytes'], 214582)
        self.assertEquals(chains['OUTPUT']['packets'], 1884)

    def testParseRules(self):
        rules = netfilter.parser.parse_rules(iptables_data, 'INPUT')
        self.assertEquals(len(rules), 1)
        self.assertEquals(rules[0].jump.name(), 'firewall_input_filter')

        rules = netfilter.parser.parse_rules(iptables_data, 'FORWARD')
        self.assertEquals(len(rules), 1)
        self.assertEquals(rules[0].jump.name(), 'firewall_forward_filter')

        rules = netfilter.parser.parse_rules(iptables_data, 'OUTPUT')
        self.assertEquals(rules, [])

class TargetTestCase(unittest.TestCase):
    def testInit(self):
        target = Target('ACCEPT')
        self.assertEqual(target.name(), 'ACCEPT')
        self.assertEqual(target.options(), {})

    def testInitOptions(self):
        target = Target('REDIRECT', '--wiz bang --foo bar')
        self.assertEqual(target.name(), 'REDIRECT')
        self.assertEqual(target.options(), {'foo': ['bar'], 'wiz': ['bang']})

    def testEqual(self):
        target1 = Target('ACCEPT', '--foo bar')
        target2 = Target('ACCEPT', '--foo bar')
        self.assertEqual(target1 == target2, True)
        self.assertEqual(target1 != target2, False)
    
    def testEqualOutOfOrder(self):
        target1 = Target('ACCEPT', '--foo bar --wiz bang')
        target2 = Target('ACCEPT', '--wiz bang --foo bar')
        self.assertEqual(target1 == target2, True)
        self.assertEqual(target1 != target2, False)

    def testNotEqualName(self):
        target1 = Target('ACCEPT', '--foo bar')
        target2 = Target('ACCEPT2', '--foo bar')
        self.assertEqual(target1 == target2, False)
        self.assertEqual(target1 != target2, True)

    def testNotEqualOptions(self):
        target1 = Target('ACCEPT')
        target2 = Target('ACCEPT', '--foo bar')
        self.assertEqual(target1 == target2, False)
        self.assertEqual(target1 != target2, True)

class MatchTestCase(unittest.TestCase):
    def testRewriteSourcePort(self):
        match = Match('tcp', '--source-port 1234')
        self.assertEqual(match.options(), {'sport': ['1234']})
    
    def testRewriteSourcePorts(self):
        match = Match('multiport', '--source-ports 1,2,3')
        self.assertEqual(match.options(), {'sports': ['1,2,3']})
    
    def testRewriteDestPorts(self):
        match = Match('tcp', '--destination-port 1234')
        self.assertEqual(match.options(), {'dport': ['1234']})
    
    def testRewriteDestPorts(self):
        match = Match('multiport', '--destination-ports 1,2,3')
        self.assertEqual(match.options(), {'dports': ['1,2,3']})

class RuleTestCase(unittest.TestCase):
    def testInit(self):
        rule = Rule(jump=Target('ACCEPT'))
        self.assertEqual(rule.protocol, None)
        self.assertEqual(rule.in_interface, None)
        self.assertEqual(rule.out_interface, None)
        self.assertEqual(rule.source, None)
        self.assertEqual(rule.destination, None)
        self.assertEqual(rule.jump.name(), 'ACCEPT')
        self.assertEqual(rule.jump.options(), {})
        self.assertEqual(rule.specbits(), ['-j', 'ACCEPT'])

    def testSource(self):
        rule = Rule(source='192.168.1.2', jump='ACCEPT')
        self.assertEqual(rule.protocol, None)
        self.assertEqual(rule.in_interface, None)
        self.assertEqual(rule.out_interface, None)
        self.assertEqual(rule.source, '192.168.1.2')
        self.assertEqual(rule.destination, None)
        self.assertEqual(rule.jump.name(), 'ACCEPT')
        self.assertEqual(rule.jump.options(), {})
        self.assertEqual(rule.specbits(), ['-s', '192.168.1.2', '-j', 'ACCEPT'])

    def testSourceNegated(self):
        rule = Rule(source='! 192.168.1.2', jump='ACCEPT')
        self.assertEqual(rule.protocol, None)
        self.assertEqual(rule.in_interface, None)
        self.assertEqual(rule.out_interface, None)
        self.assertEqual(rule.source, '! 192.168.1.2')
        self.assertEqual(rule.destination, None)
        self.assertEqual(rule.jump.name(), 'ACCEPT')
        self.assertEqual(rule.jump.options(), {})
        self.assertEqual(rule.specbits(), ['!', '-s', '192.168.1.2', '-j', 'ACCEPT'])

    def testDestination(self):
        rule = Rule(destination='192.168.1.3', jump='REJECT')
        self.assertEqual(rule.protocol, None)
        self.assertEqual(rule.in_interface, None)
        self.assertEqual(rule.out_interface, None)
        self.assertEqual(rule.source, None)
        self.assertEqual(rule.destination, '192.168.1.3')
        self.assertEqual(rule.jump.name(), 'REJECT')
        self.assertEqual(rule.jump.options(), {})
        self.assertEqual(rule.specbits(), ['-d', '192.168.1.3', '-j', 'REJECT'])

    def testDestinationNegated(self):
        rule = Rule(destination='! 192.168.1.3', jump='REJECT')
        self.assertEqual(rule.protocol, None)
        self.assertEqual(rule.in_interface, None)
        self.assertEqual(rule.out_interface, None)
        self.assertEqual(rule.source, None)
        self.assertEqual(rule.destination, '! 192.168.1.3')
        self.assertEqual(rule.jump.name(), 'REJECT')
        self.assertEqual(rule.jump.options(), {})
        self.assertEqual(rule.specbits(), ['!', '-d', '192.168.1.3', '-j', 'REJECT'])

    def testSourceDestinationProtocol(self):
        rule = Rule(source='192.168.1.2', destination='192.168.1.3',
            protocol='tcp', jump='DROP')
        self.assertEqual(rule.protocol, 'tcp')
        self.assertEqual(rule.in_interface, None)
        self.assertEqual(rule.out_interface, None)
        self.assertEqual(rule.source, '192.168.1.2')
        self.assertEqual(rule.destination, '192.168.1.3')
        self.assertEqual(rule.jump.name(), 'DROP')
        self.assertEqual(rule.jump.options(), {})
        self.assertEqual(rule.specbits(), ['-p', 'tcp', '-s', '192.168.1.2', '-d', '192.168.1.3', '-j', 'DROP'])

    def testInterfaces(self):
        rule = Rule(in_interface='eth1', out_interface='eth2',
            jump='REJECT')
        self.assertEqual(rule.protocol, None)
        self.assertEqual(rule.in_interface, 'eth1')
        self.assertEqual(rule.out_interface, 'eth2')
        self.assertEqual(rule.source, None)
        self.assertEqual(rule.destination, None)
        self.assertEqual(rule.specbits(), ['-i', 'eth1', '-o', 'eth2', '-j', 'REJECT'])

    def testInterfacesNegated(self):
        rule = Rule(in_interface='!eth1', out_interface='!eth2',
            jump='REJECT')
        self.assertEqual(rule.protocol, None)
        self.assertEqual(rule.in_interface, '!eth1')
        self.assertEqual(rule.out_interface, '!eth2')
        self.assertEqual(rule.source, None)
        self.assertEqual(rule.destination, None)
        self.assertEqual(rule.specbits(), ['!', '-i', 'eth1', '!', '-o', 'eth2', '-j', 'REJECT'])

    def testTargetLog(self):
        rule = Rule(jump=Target('LOG', '--log-prefix "ICMP accepted : " --log-level 4'))
        self.assertEqual(rule.specbits(), ['-j', 'LOG', '--log-prefix', 'ICMP accepted : ', '--log-level', '4'])

    def testMatchMark(self):
        rule = Rule(jump='ACCEPT')
        rule.matches.append(Match('mark', '--mark 0x64'))
        self.assertEqual(rule.specbits(), ['-m', 'mark', '--mark', '0x64', '-j', 'ACCEPT'])

    def testMatchMultiportDports(self):
        rule = Rule(jump='ACCEPT')
        rule.matches.append(Match('multiport', '--dports 20,21,22,80,25,1720'))
        self.assertEqual(rule.specbits(), ['-m', 'multiport', '--dports', '20,21,22,80,25,1720', '-j', 'ACCEPT'])

    def testMatchState(self):
        rule = Rule(jump='ACCEPT')
        rule.matches.append(Match('state', '--state ESTABLISHED,RELATED'))
        self.assertEqual(rule.specbits(), ['-m', 'state', '--state', 'ESTABLISHED,RELATED', '-j', 'ACCEPT'])

    def testMatchTcpFlags(self):
        rule = Rule(protocol='tcp', jump='ACCEPT')
        rule.matches.append(Match('tcp', '--tcp-flags ACK,SYN ACK'))
        self.assertEqual(rule.specbits(), ['-p', 'tcp', '-m', 'tcp', '--tcp-flags', 'ACK,SYN', 'ACK', '-j', 'ACCEPT'])

    def testMatchTcpNotFlags(self):
        rule = Rule(protocol='tcp', jump='ACCEPT')
        rule.matches.append(Match('tcp', '--tcp-flags ! ACK,SYN ACK'))
        self.assertEqual(rule.specbits(), ['-p', 'tcp', '-m', 'tcp', '--tcp-flags', '!', 'ACK,SYN', 'ACK', '-j', 'ACCEPT'])

    def testMatchTcpDport(self):
        rule = Rule(protocol='tcp', jump='ACCEPT')
        rule.matches.append(Match('tcp', '--dport 80'))
        self.assertEqual(rule.specbits(), ['-p', 'tcp', '-m', 'tcp', '--dport', '80', '-j', 'ACCEPT'])

    def testMatchTcpSport(self):
        rule = Rule(protocol='tcp', jump='ACCEPT')
        rule.matches.append(Match('tcp', '--sport 1234'))
        self.assertEqual(rule.specbits(), ['-p', 'tcp', '-m', 'tcp', '--sport', '1234', '-j', 'ACCEPT'])

    def testMatchTos(self):
        rule = Rule(jump='ACCEPT')
        rule.matches.append(Match('tos', '--tos 0x10'))
        self.assertEqual(rule.specbits(), ['-m', 'tos', '--tos', '0x10', '-j', 'ACCEPT'])

class ParseRuleTestCase(unittest.TestCase):
    def testEmpty(self):
        rule = netfilter.parser.parse_rule('')
        self.assertEqual(rule, Rule())
        self.assertEqual(rule.specbits(), [])
    
    def testGoto(self):
        rule = netfilter.parser.parse_rule('-g some_rule')
        self.assertEqual(rule, Rule(goto='some_rule'))
        self.assertEqual(rule.specbits(), ['-g', 'some_rule'])

    def testJump(self):
        rule = netfilter.parser.parse_rule('-j REJECT')
        self.assertEqual(rule, Rule(jump='REJECT'))
        self.assertEqual(rule.specbits(), ['-j', 'REJECT'])

    def testProtocol(self):
        rule = netfilter.parser.parse_rule('-p tcp')
        self.assertEqual(rule, Rule(protocol='tcp'))
        self.assertEqual(rule.specbits(), ['-p', 'tcp'])

    def testMatch(self):
        rule = netfilter.parser.parse_rule('-m state --state ESTABLISHED,RELATED')
        self.assertEqual(rule, Rule(
            matches=[Match('state', '--state ESTABLISHED,RELATED')]))
        self.assertEqual(rule.specbits(), ['-m', 'state', '--state', 'ESTABLISHED,RELATED'])

    def testSourceNegated(self):
        # iptables < 1.4.3
        rule = netfilter.parser.parse_rule('-s ! 10.1.0.0/20 -j LOG --log-prefix "Martians "')
        self.assertEqual(rule, Rule(source='! 10.1.0.0/20',jump=Target('LOG', '--log-prefix "Martians "')))

        # iptables >= 1.4.3
        rule = netfilter.parser.parse_rule('! -s 10.1.0.0/20 -j LOG --log-prefix "Martians "')
        self.assertEqual(rule, Rule(source='! 10.1.0.0/20',jump=Target('LOG', '--log-prefix "Martians "')))

    def testDestinationNegated(self):
        # iptables < 1.4.3
        rule = netfilter.parser.parse_rule('-d ! 10.1.0.0/20 -j LOG --log-prefix "Martians "')
        self.assertEqual(rule, Rule(destination='! 10.1.0.0/20',jump=Target('LOG', '--log-prefix "Martians "')))

        # iptables >= 1.4.3
        rule = netfilter.parser.parse_rule('! -d 10.1.0.0/20 -j LOG --log-prefix "Martians "')
        self.assertEqual(rule, Rule(destination='! 10.1.0.0/20',jump=Target('LOG', '--log-prefix "Martians "')))

    def testInterfacesNegated(self):
        # iptables < 1.4.3
        rule = netfilter.parser.parse_rule('-i ! eth0 -j LOG --log-prefix "Martians "')
        self.assertEqual(rule, Rule(in_interface='! eth0',jump=Target('LOG', '--log-prefix "Martians "')))

        rule = netfilter.parser.parse_rule('-o ! eth0 -j LOG --log-prefix "Martians "')
        self.assertEqual(rule, Rule(out_interface='! eth0',jump=Target('LOG', '--log-prefix "Martians "')))

        # iptables >= 1.4.3
        rule = netfilter.parser.parse_rule('! -i eth0 -j LOG --log-prefix "Martians "')
        self.assertEqual(rule, Rule(in_interface='! eth0',jump=Target('LOG', '--log-prefix "Martians "')))

        rule = netfilter.parser.parse_rule('! -o eth0 -j LOG --log-prefix "Martians "')
        self.assertEqual(rule, Rule(out_interface='! eth0',jump=Target('LOG', '--log-prefix "Martians "')))

    def testProtocolNegated(self):
        # iptables < 1.4.3
        rule = netfilter.parser.parse_rule('-p ! tcp -j LOG --log-prefix "Martians "')
        self.assertEqual(rule, Rule(protocol='! tcp',jump=Target('LOG', '--log-prefix "Martians "')))

        # iptables >= 1.4.3
        rule = netfilter.parser.parse_rule('! -p tcp -j LOG --log-prefix "Martians "')
        self.assertEqual(rule, Rule(protocol='! tcp',jump=Target('LOG', '--log-prefix "Martians "')))

class BufferedTestCase(unittest.TestCase):
    def testJump(self):
        table = netfilter.table.Table('test_table', False)
        table.append_rule('test_chain', Rule(jump='ACCEPT'))
        buffer = table.get_buffer()
        self.assertEqual(buffer, [['iptables', '-t', 'test_table', '-A', 'test_chain', '-j', 'ACCEPT']])

if __name__ == '__main__':
    unittest.main()
