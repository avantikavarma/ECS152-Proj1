# previous sender utilized a GBN strategy which was nested loops
# doesn't exactly work well -- slow, but also unusable given a TCP Reno EC
# currently implementing a queue based sender instead

import socket
import time
import math
from collections import deque 

SEQ_ID_SIZE = 4
MESSAGE_SIZE = 1020
# WINDOW_SIZE = 100 * MESSAGE_SIZE # window size is now a variable -- look for cwnd instead

def print_deque(packet_in_flight):
    for i in packet_in_flight:
        print(i)

def sender():
    # file to be sent
    file_path = "file.mp3"

    # read the file
    # print("Reading file")
    with open(file_path, "rb") as f:
        file_data = f.read() # Read whole file for easier indexing
    file_len = len(file_data)
    # print("file_len = ", file_len)

    # track the packets
    packet_in_flight = deque()
    # use a deque, originally used two loops, but this works better
    send_time = {} # first send time of a packet, will not get reset
    delays = [] # appending all of the delays, will average
    packet_next = 0 # next packet to send -- byte

    # set init conditions for TCP Reno
    last_ack = 0
    num_last_ack = 0
    cwnd = 1 * MESSAGE_SIZE
    ssthresh = 64 * MESSAGE_SIZE
    fast_recovery = False

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.settimeout(1)

        transfer_start_time = time.time()
        
        while packet_next < file_len or packet_in_flight:
            # SEND DATA
            while len(packet_in_flight) * MESSAGE_SIZE < cwnd and packet_next < file_len:
                msg = file_data[packet_next : packet_next + MESSAGE_SIZE] 
                header = packet_next.to_bytes(4, byteorder='big', signed=True)

                # mark package as in flight
                packet_in_flight.append(packet_next)

                # timestamp when it goes into flight
                if packet_next not in send_time:
                    send_time[packet_next] = time.time()
                    # print("Sent: ", packet_next, " at: ", send_time[packet_next])

                # send packet
                udp_socket.sendto(header + msg, ("127.0.0.1", 5001))
                packet_next += MESSAGE_SIZE
            
            # RECIEVE ACK
            try:
                ack_packet, throwaway = udp_socket.recvfrom(1024) # receive ack ('ack' is 3 bytes, 4 bytes for actual)
                ack_id = int.from_bytes(ack_packet[:4], byteorder='big', signed=True) 
                ack_time = time.time()
                # print("ACK: ", ack_id, "  LAST_ACK: ", last_ack)

                # BASE CASE
                if ack_id > last_ack:
                    # SHIFT WINDOW
                    while packet_in_flight and packet_in_flight[0] < ack_id:
                        seq_id = packet_in_flight.popleft()
                        # print("Clear from queue: ", seq_id)
                        # print("Left in queue: ")
                        # print_deque(packet_in_flight)
                        if seq_id in send_time:
                            delays.append(ack_time - send_time[seq_id])
                    # Exit Fast Recovery
                    if fast_recovery:
                        fast_recovery = False
                        cwnd = ssthresh # reset the cwnd back to ssthresh (deflate it)
                    # SLOW START
                    elif cwnd < ssthresh:
                        cwnd += MESSAGE_SIZE
                        # print("ss cwnd: ", cwnd, "  ssthresh: ", ssthresh)
                    # AIMD -- Additive Increase
                    else:
                        cwnd += MESSAGE_SIZE * MESSAGE_SIZE / cwnd
                        # print("aimd cwnd: ", cwnd, "  ssthresh: ", ssthresh)

                    last_ack = ack_id
                    num_last_ack = 0
                    
                # Check for dupe
                elif ack_id == last_ack:
                    num_last_ack += 1
                    # print("dupe for : ", ack_id, "  #", num_last_ack)

                    # FAST RETRANSMIT condition
                    if num_last_ack == 3:
                        # print("FAST RETRANSMIT TRIGGERED: ", ack_id)
                        # print("pre cwnd: ", cwnd, "  pre ssthresh: ", ssthresh)
                        ssthresh = math.floor(cwnd/2)
                        cwnd = ssthresh
                        # print("post cwnd: ", cwnd, "  post ssthresh: ", ssthresh)
                        # FAST RECOVERY action == retransmit the last package
                        msg = file_data[ack_id : ack_id + MESSAGE_SIZE] 
                        header = ack_id.to_bytes(4, byteorder='big', signed=True)
                        udp_socket.sendto(header + msg, ("127.0.0.1", 5001))
                        fast_recovery = True
                    # Extra Duplicate ACK, increase cwnd
                    elif num_last_ack >= 3:
                        # print("extra dupe cwnd: ", cwnd, "  extra dupe ssthresh: ", ssthresh)
                        cwnd += MESSAGE_SIZE
                
                # FINACK
                if ack_id == file_len and not packet_in_flight:
                    # print("FINACK")
                    packet_start = -1
                    fin_header = packet_start.to_bytes(4, byteorder='big', signed=True)
                    fin_msg = b"==FINACK=="
                    udp_socket.sendto(fin_header + fin_msg, ("127.0.0.1", 5001))
                    break

            # TIMEOUT
            except socket.timeout:
                # print("TIMEOUT ack_id: ", ack_id)
                # print("num_last_ack:   ", num_last_ack)
                # print("queue size:     ", len(packet_in_flight))

                # print("pre, cwnd: ", cwnd, " ssthresh: ", ssthresh)

                # resend everything that's in the queue
                for seq_id in packet_in_flight:
                    # print("Timeout resent: ", seq_id)
                    msg = file_data[seq_id : seq_id + MESSAGE_SIZE] 
                    header = seq_id.to_bytes(4, byteorder='big', signed=True)
                    udp_socket.sendto(header + msg, ("127.0.0.1", 5001))
                
                # reset everything for slow start on teimeout
                ssthresh = math.floor(cwnd/2)
                cwnd = MESSAGE_SIZE

                # print("post, cwnd: ", cwnd, " ssthresh: ", ssthresh)
        
        transfer_end_time = time.time()    

    transfer_time = transfer_end_time - transfer_start_time
    throughput = file_len/transfer_time
    per_packet_delay = sum(delays)/len(delays)
    performance = 0.3*(throughput/1000) + 0.7*(1/per_packet_delay)
    # print("Transfer Time: ", transfer_time)
    # print("Throughput: ", throughput)
    # print("Per_Packet_Delay: ", per_packet_delay)
    # print("Performance: ", performance)
    print(throughput, ', ', per_packet_delay, ', ', performance)

def main():
    sender()

main()
