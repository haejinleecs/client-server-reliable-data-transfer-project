#!/usr/bin/env python3
import sys
import time
import socket
import datetime 

CONNECTION_TIMEOUT = 60

# for testing with gaia server
SERVER_IP = "128.119.245.12"
SERVER_PORT = 20008

def checksum(msg):
    """
     This function calculates checksum of an input string
     Note that this checksum is not Internet checksum.
    
     Input: msg - String
     Output: String with length of five
     Example Input: "1 0 That was the time fo "
     Expected Output: "02018"
    """

    # step1: covert msg (string) to bytes
    msg = msg.encode("utf-8")
    s = 0
    # step2: sum all bytes
    for i in range(0, len(msg), 1):
        s += msg[i]
    # step3: return the checksum string with fixed length of five 
    #        (zero-padding in front if needed)
    return format(s, '05d')

def checksum_verifier(msg):
    """
     This function compares packet checksum with expected checksum
    
     Input: msg - String
     Output: Boolean - True if they are the same, Otherwise False.
     Example Input: "1 0 That was the time fo 02018"
     Expected Output: True
    """

    expected_packet_length = 30
    # step 1: make sure the checksum range is 30
    if len(msg) < expected_packet_length:
        return False
    # step 2: calculate the packet checksum
    content = msg[:-5]
    calc_checksum = checksum(content)
    expected_checksum = msg[-5:]
    # step 3: compare with expected checksum
    if calc_checksum == expected_checksum:
        return True
    return False

def start_receiver(connection_ID, loss_rate=0.0, corrupt_rate=0.0, max_delay=0.0):
    """
     This function runs the receiver, connect to the server, and receiver file from the sender.
     The function will print the checksum of the received file at the end. 
     The file checksum is expected to be the same as the checksum that the sender prints at the end.

     Input: 
        connection_ID - String
        loss_rate - float (default is 0, the value should be between [0.0, 1.0])
        corrupt_rate - float (default is 0, the value should be between [0.0, 1.0])
        max_delay - int (default is 0, the value should be between [0, 5])
     Output: None
    """

    # Name and datetime
    name = "Haejin Lee"
    print("START receiver - {} @ {}".format(name, datetime.datetime.now()))

    # Creat client socket
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Set connection timeout
    clientSocket.settimeout(CONNECTION_TIMEOUT)
    try:
        # Connect client to server
        clientSocket.connect((SERVER_IP,SERVER_PORT))
    except socket.error as e:
        # Handle error and terminate
        print('Connection error: {}'.format(e))
        clientSocket.close()
        return
    # Disable timeout 
    clientSocket.settimeout(None)
    # Request a relay service
    message = "HELLO R {} {} {} {}".format(loss_rate, corrupt_rate, max_delay, connection_ID)
    clientSocket.sendall(message.encode("utf-8"))
    # Wait for message
    recv_message = clientSocket.recv(1024).decode("utf-8")
    print("received: {}".format(recv_message))
    # Check response and keep waiting or terminate if the respond is not OK
    while not recv_message.startswith("OK"):
        if recv_message.startswith("WAITING"):
            # Wait
            print("Waiting for a sender")
            recv_message = clientSocket.recv(1024).decode("utf-8")
            
        elif recv_message.startswith("ERROR"):
            # Print error and terminate
            print("Error: {}".format(recv_message[6:]))
            return
        else: # Invalid message, print and temrinate
            print("Error: Invalid message format from server during connection phrase... {}".format(recv_message))
            return

    print("ESTABLISHED A CHANNEL @ {}".format(datetime.datetime.now()))

    # STEP 2: Receive file
    
    ACK = 0
    data = ""
    total_packet_sent = 0
    total_packet_recv = 0
    total_corrupted_pkt_recv = 0

    ####################################################
    # RDT 3.0 RECEIVER IMPLEMENTATION BELOW #
    ####################################################

    while True:
        # Receiver keeps receiving a message from sender
        recv_msg = clientSocket.recv(30).decode("utf-8")
        print("--> receiver received {} @ {}".format(recv_msg, datetime.datetime.now()))
        recv_arr = recv_msg.split()

        if len(recv_msg)<2: # if the message is empty, terminate
            break
        
        recv_SEQ = recv_arr[0]
        print('received SEQ {}'.format(recv_SEQ))
        total_packet_recv+=1

        # packet is corrupt if checksum_verifier returns false
        corrupt = not checksum_verifier(recv_msg) 

        # while receiver receives a corrupt or incorrect package; receiver stays within the wait for 0/1 state
        while corrupt or int(recv_SEQ) != int(ACK):
            # if the packet is corrupt
            if corrupt:
                total_corrupted_pkt_recv+=1
                print("corrupt packet!")
            
            # set the recv_SEQ # that will be sent in the packet (recv_SEQ could have miscellaneous characters)
            if ACK == 1:
                recv_SEQ = 0
            else:
                recv_SEQ = 1

            # send_pkt is created with ACK
            send_pkt = '  '+str(recv_SEQ)+'                      '
            # compute and append checksum
            recv_checksum = checksum(send_pkt)
            send_pkt += recv_checksum
            # send the packet
            clientSocket.send(send_pkt.encode("utf-8")) 
            total_packet_sent += 1 # increment total packets sent
            print("<-- receiver sent {} @ {}".format(send_pkt, datetime.datetime.now()))

            # receiver tries to receive a new packet and while loop reruns
            recv_msg = clientSocket.recv(30).decode("utf-8")
            if len(recv_msg) < 2:
                break
            print("--> receiver received {} @ {}".format(recv_msg, datetime.datetime.now()))
            recv_arr = recv_msg.split()
            recv_SEQ = recv_arr[0]
            print('received SEQ {}'.format(recv_SEQ))
            # corrupt is updated
            corrupt = not checksum_verifier(recv_msg)
            total_packet_recv+=1

        # Once receiver receives an uncorrupt packet w/ correct checksum; receiver moves out of wait state

        # receiver creates new send_pkt
        data+=recv_msg[4:-6]
        send_pkt = '  '+str(recv_SEQ)+'                      '
        # add checksum
        recv_checksum=checksum(send_pkt) 
        send_pkt+=recv_checksum
        ACK = 1 if ACK == 0 else 0 # update ACK # 
        
        # receiver sends new packet
        clientSocket.send(send_pkt.encode("utf-8")) 
        total_packet_sent+=1
        print("<-- receiver sent {} with ACK {} @ {}".format(send_pkt, recv_SEQ, datetime.datetime.now()))

    # close the socket
    clientSocket.close() 

    # remove space at the end
    data = data.rstrip(' ')

    # print out name, date and time
    print("DONE receiver - {} @ {}".format(name, datetime.datetime.now()))
    # print packet information
    print("File checksum: {}".format(checksum(data)))
    print("Total packet sent: {}".format(total_packet_sent))
    print("Total packet recv: {}".format(total_packet_recv))
    print("Total corrupted packet recv: {}".format(total_corrupted_pkt_recv))
 
if __name__ == '__main__':
    # check arguments
    if len(sys.argv) != 5:
        print("Expected \"python PA2_receiver.py <connection_id> <loss_rate> <corrupt_rate> <max_delay>\"")
        exit()

    # assign arguments
    connection_ID, loss_rate, corrupt_rate, max_delay = sys.argv[1:]

    # START RECEIVER
    start_receiver(connection_ID, loss_rate, corrupt_rate, max_delay)