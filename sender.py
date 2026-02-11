import socket
import struct
import time

SEQ_ID_SIZE = 4
MESSAGE_SIZE = 1020
WINDOW_SIZE = 100 * MESSAGE_SIZE


def main():
    start = time.time() # start timer
    print("Start Time: ", start)

    # file to be sent
    file_path = "/Users/derekzhang/Documents/EEC173A/Project #1/2024_congestion_control_ecs152a/docker/file.mp3"

    # read the file
    # print("Reading file")
    with open(file_path, "rb") as f:
        file_data = f.read() # Read whole file for easier indexing
    file_len = len(file_data)
    # print("file_len = ", file_len)

    # make the socket
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.settimeout(1)
        # print("Socket started")

        window_start = 0 # starting byte of current window
        packet_start = 0 # starting byte of current packet
        ack_id = 0 

        while window_start < file_len:
            # IMPORTANT! make sure to match the start of the packet to the window each iteration
            # Didn't do this originally and it ended up skipping because they weren't matched up
            packet_start = window_start 

            # Try to send as many packets as the window lets, or until the end of the file
            while packet_start < window_start + WINDOW_SIZE and packet_start < file_len:
                msg = file_data[packet_start : packet_start + MESSAGE_SIZE] # the actual message
                header = packet_start.to_bytes(4, byteorder='big', signed=True) # header to the message, align the same way as receiver takes it in
                udp_socket.sendto(header + msg, ("127.0.0.1", 5001))

                # print("Bytes: ", packet_start, " to ", packet_start + MESSAGE_SIZE)
                packet_start += len(msg) # increment current packet
            try:
                ack_packet, throw_ADDR = udp_socket.recvfrom(7) # receive ack ('ack' is 3 bytes, 4 bytes for actual)
                ack_id = int.from_bytes(ack_packet[:4], byteorder='big', signed=True) 
                # print("Receiver wants", ack_id)

                if ack_id > window_start: # shift the window over
                    window_start = ack_id
            except socket.timeout: # timeout, send from the new start of the window (assuming window has slid over a bit)
                packet_start = window_start
                # print("timeout -- resending from", packet_start)

        # fin
        packet_start = -1
        fin_header = packet_start.to_bytes(4, byteorder='big', signed=True)
        fin_msg = b"==FINACK=="
        udp_socket.sendto(fin_header + fin_msg, ("127.0.0.1", 5001))
    end = time.time()

    print("End Time: ", end)
    print("Total Time: ", end - start)

main()