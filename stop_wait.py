import socket
import time
import sys

# settings general 
SEQ_ID_SIZE = 4            # Number of bytes used for the sequence ID header
MESSAGE_SIZE = 1020        # Max size of data payload per packet
RECEIVER_ADDR = ("127.0.0.1", 5001) # Target IP and receiver port 
SENDER_PORT = 6000         # Local port for sender
TIMEOUT = 0.5              # Time to wait before retransmitting the ACK 

def main():
    file_path = "file2.mp3" 
    # Load the file into memory as bytes
    try:
        with open(file_path, "rb") as f:
            file_data = f.read()
    except FileNotFoundError:
        return

    file_len = len(file_data)
    
    start_time = time.time()
    packet_delays = []
    total_bytes_sent = 0

    # Initialize UDP socket
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.bind(("0.0.0.0", SENDER_PORT))
        udp_socket.settimeout(TIMEOUT)

        byte_offset = 0 

        # Main loop: Iterate through the file data in chunks
        while byte_offset < file_len:
            # Slice the data and create the 4-byte sequence header, basically the byte offset
            chunk = file_data[byte_offset : byte_offset + MESSAGE_SIZE]
            header = byte_offset.to_bytes(4, byteorder='big', signed=True)
            packet = header + chunk
            
            acked = False
            first_send_attempt_time = time.time() 

            # Keep sending until a valid ACK is received
            while not acked:
                udp_socket.sendto(packet, RECEIVER_ADDR) 
                
                try:
                    # Wait for acknowledgement from the receiver
                    ack_packet, _ = udp_socket.recvfrom(1024)
                    ack_id = int.from_bytes(ack_packet[:4], byteorder='big', signed=True)
                    
                    current_delay = time.time() - first_send_attempt_time

                    # If ACK confirms receipt of current or more data, move forward
                    if ack_id >= byte_offset + len(chunk):
                        packet_delays.append(current_delay)
                        total_bytes_sent += len(chunk)
                        byte_offset = ack_id 
                        acked = True
                    
                    # If receiver is asking for an older byte, roll back offset
                    elif ack_id < byte_offset:
                        byte_offset = ack_id
                        acked = True 

                except socket.timeout:
                    # If timeout occurs, loop restarts and packet is re-sent
                    pass

        # FIN Phase: Send a termination signal to notify the receiver that the file is done
        fin_header = (-1).to_bytes(4, byteorder='big', signed=True)
        udp_socket.sendto(fin_header + b"==FINACK==", RECEIVER_ADDR)

    end_time = time.time()
    total_time = end_time - start_time
    
    # Calculate performance metrics - performance_metric = 0.3 * (throughput / 1000) + 0.7 * (1 / avg_delay)
    throughput = total_bytes_sent / total_time
    avg_delay = sum(packet_delays) / len(packet_delays) if packet_delays else 0
    performance_metric = 0.3 * (throughput / 1000) + 0.7 * (1 / avg_delay) if avg_delay > 0 else 0

    # Print only the final results as comma-separated values
    print(f"{throughput:.7f}", f"{avg_delay:.7f}", f"{performance_metric:.7f}", sep=", ")

if __name__ == "__main__":
    main()
