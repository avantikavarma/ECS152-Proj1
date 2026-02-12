import socket
import time
import sys

# Configuration settings for network communication
SEQ_ID_SIZE = 4            # Number of bytes used for the sequence ID header
MESSAGE_SIZE = 1020        # Max size of data payload per packet
RECEIVER_ADDR = ("127.0.0.1", 5001) # Target IP and receiver port 
SENDER_PORT = 6000         # Local port for sender
TIMEOUT = 0.5              # Time to wait beofre retransmitting the ACK 

def main():
    file_path = "file2.mp3" 
    #   open and read the entire file into memory
    try:
        with open(file_path, "rb") as f:
            file_data = f.read()
    except FileNotFoundError:
        print(f"Error: {file_path} not found.")
        return

    file_len = len(file_data)
    
    # Initialize variables for performance tracking
    start_time = time.time()
    packet_delays = []
    total_bytes_sent = 0

    # Create a UDP socket (SOCK_DGRAM) and bind it to the local port
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.bind(("0.0.0.0", SENDER_PORT))
        udp_socket.settimeout(TIMEOUT) # Set the non-blocking timeout limit

        byte_offset = 0 # Tracks our current progress through the file

        print(f"Starting Stop-and-Wait: {file_len} bytes")

        # Continues until all data is acknowledged
        while byte_offset < file_len:
            # Prepare the current chunk of data
            chunk = file_data[byte_offset : byte_offset + MESSAGE_SIZE]
            # create and add header using the current byte offset 
            header = byte_offset.to_bytes(4, byteorder='big', signed=True)
            packet = header + chunk
            
            acked = False
            first_send_attempt_time = time.time() # Start timer for Round Trip Time (RTT)

            # if ACKs are lost
            while not acked:
                udp_socket.sendto(packet, RECEIVER_ADDR) # Send packet to receiver
                
                try:
                    # Wait for acknowledgement from the receiver
                    ack_packet, _ = udp_socket.recvfrom(1024)
                    ack_id = int.from_bytes(ack_packet[:4], byteorder='big', signed=True)
                    
                    # Calculate how long it took for this specific packet cycle
                    current_delay = time.time() - first_send_attempt_time

                    # If the ACK covers the current chunk - move the offset forward
                    if ack_id >= byte_offset + len(chunk):
                        packet_delays.append(current_delay)
                        total_bytes_sent += len(chunk)
                        byte_offset = ack_id 
                        acked = True
                    
                    # If the receiver is asking for a previous offset then jump back
                    elif ack_id < byte_offset:
                        byte_offset = ack_id
                        acked = True 

                    print(f"Sent: {byte_offset} | Delay: {current_delay:.4f}s", end="\r")

                except socket.timeout:
                    # No response within TIMEOUT seconds; loop restarts to send again
                    print(f"\n[!] Timeout at {byte_offset}. Retrying...")

        # FIN Phase 
        # Signal receiver that the file transfer is finished
        fin_header = (-1).to_bytes(4, byteorder='big', signed=True)
        udp_socket.sendto(fin_header + b"==FINACK==", RECEIVER_ADDR)

    # calculate total time and end time 
    end_time = time.time()
    total_time = end_time - start_time
    
    # Calculate bytes sent per second
    throughput = total_bytes_sent / total_time
    
    # mean time calculation for packet-ACK cycles
    avg_delay = sum(packet_delays) / len(packet_delays) if packet_delays else 0
    
    # formula for assignment 
    performance_metric = 0.3 * (throughput / 1000) + 0.7 * (1 / avg_delay) if avg_delay > 0 else 0

    # final results to the console
    print("\n" + "="*30)
    print(f"TRANSFER COMPLETE")
    print(f"Total Time:     {total_time:.4f} seconds")
    print(f"Throughput:     {throughput:.2f} bytes/s")
    print(f"Average Delay:  {avg_delay:.4f} seconds")
    print(f"Performance:    {performance_metric:.4f}")
    print("="*30)

if __name__ == "__main__":
    main()
