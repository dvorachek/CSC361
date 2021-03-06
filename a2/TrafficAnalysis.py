# Dylan Dvorachek
# V00863468
# CSC 361 A2

import pcapy
import sys
import socket
from struct import *
import datetime
from collections import OrderedDict


# Holds and organizes packet data
data = OrderedDict()

# Function which takes in source/destination IPs and Ports
# and initalizes a dictionary with them. This is then added
# to 'data' as a value with a unique key.
def data_init(s_addr, d_addr, s_port, d_port):
    d = {'s_addr': s_addr,
         'd_addr': d_addr,
         's_port': s_port,
         'd_port': d_port,
         'fin': 0,
         'syn': 0,
         'rst': 0,
         'packet_out': 0,
         'packet_in': 0,
         'data_out': 0,
         'data_in': 0,
         'time_out': [],
         'time_in': [],
         'time': [],
         'window': [],
         'RTT': [],
         'last_fin_time': 0
        }
    return d

# Reads in packet header/payload and parses information into the 
# ordered dictionary 'data'.
# At the end the calculate RTT function is called.
def parse_payload(header, payload):
    time = header.getts()

    # ethernet header = 14, ip header = 20
    iph = unpack('!BBHHHBBH4s4s', payload[14:34])

    iph_len = (iph[0] & 0xF) * 4
    
    s_addr = socket.inet_ntoa(iph[8])
    d_addr = socket.inet_ntoa(iph[9])
    
    tcphead = payload[iph_len+14:iph_len+34]
    tcph = unpack('!HHLLBBHHH', tcphead)
    s_port = tcph[0]
    d_port = tcph[1]
    tcp_len = tcph[4] >> 4
    
    data_sent = header.getlen() - (14 + iph_len + tcp_len * 4)
    
    flags = tcph[5]
    fin = flags & 0x01
    syn = (flags & 0x02) >> 1
    rst = (flags & 0x04) >> 2
    psh = (flags & 0x08) >> 3
    
    window = tcph[6]

    # unique identifier for each connection
    id = ''.join(item for item in sorted([s_addr, d_addr, str(s_port), str(d_port)]))
    
    # create data structure entry
    if id not in data:
        data[id] = data_init(s_addr, d_addr, s_port, d_port)
        
    if fin:
        data_sent = 0
        data[id]['last_fin_time'] = time

    # update data structure
    data[id]['fin'] += fin
    data[id]['syn'] += syn
    data[id]['rst'] += rst

    if s_port == data[id]['s_port']:
        data[id]['packet_out'] += 1
        data[id]['data_out'] += data_sent
        data[id]['time_out'].append(time)
    else:
        data[id]['packet_in'] += 1
        data[id]['data_in'] += data_sent
        data[id]['time_in'].append(time)

    data[id]['time'].append(time)
    data[id]['window'].append(window)
    
    calc_RTT(id)  # in ms

# Appends a new RTT value from the latest
# Uses an alpha of 0.25
def calc_RTT(id):
    alpha = 0.25
    
    if data[id]['RTT']:
        data[id]['RTT'].append(((1 - alpha) * data[id]['RTT'][-1]) + (alpha * (abs(make_time(data[id]['time_in'][-1]) - make_time(data[id]['time_out'][-1])))))
    elif data[id]['time_in'] and data[id]['time_out']:
        data[id]['RTT'].append(abs(make_time(data[id]['time_in'][-1]) - make_time(data[id]['time_out'][-1])))

# Helper method for converting (second, millisecond) tuple into seconds.
def make_time(time):
    return (time[0] + (float(time[1])/1000000)) * 1000  # RTT in ms

# Formats and prints output from OrderedDict 'data'
def output_results():
    print("Total number of connections: {}\n".format(len(data)))
    
    reset_connections = 0
    complete_connections = 0
    all_times = []
    all_RTT = []
    all_packets = []
    all_windows = []
    i = 1
    # Part A
    for key, v in data.items():
        print("Connection {}:".format(i))
        print("Source Address: {}".format(data[key]['s_addr']))
        print("Destination Address: {}".format(data[key]['d_addr']))
        print("Source Port: {}".format(data[key]['s_port']))
        print("Destination Port: {}".format(data[key]['d_port']))
        print("Status: S{}F{}  R{}".format(data[key]['syn'], data[key]['fin'], data[key]['rst']))
        
        if data[key]['rst']:
            reset_connections += 1
        i += 1
        
        # Part B
        if data[key]['fin'] and data[key]['syn']:
            time = data[key]['time']
            e_time = data[key]['last_fin_time']
            start_time = time[0][0] + (float(time[0][1])/1000000)
            end_time = e_time[0] + (float(e_time[1])/1000000)
            duration = end_time - start_time
            print("Start Time: {}".format(datetime.datetime.fromtimestamp(start_time)))
            print("End Time: {}".format(datetime.datetime.fromtimestamp(end_time)))
            print("Duration: {}".format(duration))
            print("Number of packets sent from Source to Destination: {}".format(data[key]['packet_out']))
            print("Number of packets sent from Destination to Source: {}".format(data[key]['packet_in']))
            print("Total number of packets: {}".format(data[key]['packet_out'] + data[key]['packet_in']))
            print("Number of data bytes sent from Source to Destination: {}".format(data[key]['data_out']))
            print("Number of data bytes sent from Destination to Source: {}".format(data[key]['data_in']))
            print("Total number of data bytes: {}".format(data[key]['data_out'] + data[key]['data_in']))
            complete_connections += 1
            all_times.append(duration)
            [all_RTT.append(item) for item in data[key]['RTT']]
            all_packets.append(data[key]['packet_out'] + data[key]['packet_in'])
            [all_windows.append(item) for item in data[key]['window']]
            
        print('\n')
    
    # Part C
    print("Total number of complete TCP connections: {}".format(complete_connections))
    print("Number of reset TCP connections: {}".format(reset_connections))
    print("Number of TCP connections that were still open when the trace capture ended: {}\n".format(len(data)-complete_connections))
    
    # Part D
    print("Minimum time duration: {0:.6f}s".format(min(all_times)))
    print("Mean time duration: {0:.6f}s".format(sum(all_times)/len(all_times)))
    print("Maximum time duration: {0:.6f}s\n".format(max(all_times)))
    
    print("Minimum RTT value: {}ms".format(int(min(all_RTT))))
    print("Mean RTT value: {0:.2f}ms".format(sum(all_RTT)/len(all_RTT)))
    print("Maximum RTT value: {}ms\n".format(int(max(all_RTT))))
    
    print("Minimum number of packets including both send/received: {}".format(min(all_packets)))
    print("Mean number of packets including both send/received: {0:.2f}".format(sum(all_packets)/len(all_packets)))
    print("Maximum number of packets including both send/received: {}\n".format(max(all_packets)))
    
    print("Minimum receive window size including both send/received: {}".format(min(all_windows)))
    print("Mean receive window size including both send/received: {0:.2f}".format(sum(all_windows)/len(all_windows)))
    print("Maximum receive window size including both send/received: {}\n".format(max(all_windows)))


def main(argv):
    try:
        cap = pcapy.open_offline(argv[1])
    except:
        print("Failed to open the specified cap file")
        exit(1)
        
    (header, payload) = cap.next()
    
    while header:
        parse_payload(header, payload)
        (header, payload) = cap.next()
    
    output_results()     


if __name__=="__main__":
    if len(sys.argv) < 2:
        print("Requires an additional argument specifying a cap file")
        exit(1)
    main(sys.argv)

