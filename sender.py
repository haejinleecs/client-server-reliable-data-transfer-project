#!/usr/bin/env python3
# Last updated: Apr, 2023
# Author: Haejin Lee
import sys
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

def start_sender(connection_ID, loss_rate=0, corrupt_rate=0, max_delay=0, transmission_timeout=60):
    """
     This function runs the sender, connnect to the server, and send a file to the receiver.
     The function will print the checksum, number of packet sent/recv/corrupt recv/timeout at the end. 
     The checksum is expected to be the same as the checksum that the receiver prints at the end.

     Input: 
        connection_ID - String
        loss_rate - float (default is 0, the value should be between [0.0, 1.0])
        corrupt_rate - float (default is 0, the value should be between [0.0, 1.0])
        max_delay - int (default is 0, the value should be between [0, 5])
        tranmission_timeout - int (default is 60 seconds and cannot be 0)
     Output: None
    """

    ## STEP 0: PRINT YOUR NAME AND DATE TIME
    name = "Haejin Lee"
    print("START receiver - {} @ {}".format(name, datetime.datetime.now()))

    ## STEP 1: CONNECT TO THE SERVER
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # set connection timeout
    clientSocket.settimeout(CONNECTION_TIMEOUT)
    try:
        # connect to the server
        clientSocket.connect((SERVER_IP,SERVER_PORT))
    except socket.error as e:
        # print error and terminate if fail
        print('Connection error: {}'.format(e))
        clientSocket.close()
        sys.exit()
    # disable timeout 
    clientSocket.settimeout(None)
    # request a relay service
    message = "HELLO S {} {} {} {}".format(loss_rate, corrupt_rate, max_delay, connection_ID)
    clientSocket.sendall(message.encode("utf-8"))
    print("sending: {}".format(message))
    # wait for message
    recv_message = clientSocket.recv(1024).decode("utf-8")
    print("received: {}".format(recv_message))
    # check response and keep waiting or terminate if the respond is not OK
    while not recv_message.startswith("OK"):
        if recv_message.startswith("WAITING"):
            # wait
            print("Waiting for a receiver")
            recv_message = clientSocket.recv(1024).decode("utf-8")
            
        elif recv_message.startswith("ERROR"):
            # print error and terminate
            print("Error: {}".format(recv_message.split(' ')[1]))
            exit()
        else:
            # invalid message, print and temrinate
            print("Error: Invalid message from server during connection. The message is {}".format(recv_message))
            exit()

    print("ESTABLISHED A CHANNEL @ {}".format(datetime.datetime.now()))

    ## STEP 2: READ FILE
    # read file
    filename = 'declaration.txt'
    with open(filename, 'r') as f:
        data = f.read()

    # some helpful variables but you don't have to use all of them
    pointer = 0
    SEQ = 0
    ACK = 0
    total_packet_sent = 0
    total_packet_recv = 0
    total_corrupted_pkt_recv = 0
    total_timeout =  0
    
    # set transmission timeout (set to 3 seconds if input is less or equal to zero)
    if transmission_timeout <= 0:
        transmission_timeout = 3
    clientSocket.settimeout(transmission_timeout)

    # send the first 200 characters
    to_send_size = 200

    # STEP 3: SEND FILE

    ##################################################
    # START YOUR RDT 3.0 SENDER IMPLEMENTATION BELOW #
    ##################################################

    # Helper function that creates a new packet given SEQ, ACK, and data
    def create_pkt(SEQ, ACK, data):
        string = ''
        # get next 20 bytes in Declaration of Independence
        for s in data: # iterate through data from pointer forward
            if len(string) == 20: 
                break
            string+=s

        # append SEQ, ACK and data
        pkt = str(SEQ)+' '+str(ACK)+' '+string+' ' # get next 20 bytes in text file

        # compute checksum of pkt
        ch = checksum(pkt)

        # append checksum to the packet to be sent
        pkt+=ch 

        return pkt # return created packet
    
    # START: sender creates a packet
    send_pkt = create_pkt(SEQ, ACK, data[pointer:]) 
    pointer+=20 # increment pointer in the text file

    while to_send_size > 0:
        # sender sends packet
        clientSocket.send(send_pkt.encode("utf-8"))
        # increment total packets sent
        total_packet_sent+=1
        # decrement packets to be sent
        to_send_size-=20

        # change SEQ after sending current SEQ
        if SEQ==1:
            SEQ=0
        else:
            SEQ=1
        print("<-- sender sent message {} at {}".format(send_pkt, datetime.datetime.now()))

        # set timer
        clientSocket.settimeout(transmission_timeout)
        

        try: 
            # in wait for call 0/wait for call 1 state: try to receive packet
            recv_msg = clientSocket.recv(30).decode("utf-8")
            print("--> sender received message {} at {}".format(recv_msg, datetime.datetime.now()))
            
            recv_pkt = recv_msg.split()

            # in Wait For ACK0/ACK1 State
            if len(recv_msg)<2:
                break

            recv_ACK = recv_pkt[0]
            print('recv_ACK = {}, ACK = {}'.format(recv_ACK, ACK))

            corrupt = not checksum_verifier((recv_msg))

            # check if received corrupt packet or incorrect ACK
            while corrupt or int(recv_ACK)!=int(ACK):
                # if corrupt
                if corrupt:
                    total_corrupted_pkt_recv+=1 # increment corrupt packet count
                    print("received corrupt packet!")
                    recv_ACK = 1 if ACK == 0 else 0
                else:
                    print("received packet with wrong ACK or SEQ number")
                total_packet_recv+=1
                recv_ACK=int(recv_ACK)

                clientSocket.send(send_pkt.encode("utf-8"))
                # increment total packets sent
                total_packet_sent+=1
                print("<-- sender resent same packet {} at {}".format(send_pkt, datetime.datetime.now()))

                # receive another packet
                recv_msg = clientSocket.recv(30).decode("utf-8")
                print("--> sender received NEW message {} at {}".format(recv_msg, datetime.datetime.now()))
                recv_pkt = recv_msg.split()
                if len(recv_msg)<2:
                    break
                recv_ACK = recv_pkt[0]
                corrupt = not checksum_verifier((recv_msg))

            # if uncorrupt packet and correct ACK
            if (not corrupt) and ACK==int(recv_ACK): 
                # change ACK that we expect to get next
                if ACK == 1: 
                    ACK=0
                else:
                    ACK=1
                print("received uncorrupt package! New SEQ {}, new ACK {}".format(SEQ,ACK))
                total_packet_recv+=1
                send_pkt = create_pkt(SEQ, ACK, data[pointer:])
                pointer+=20 # increment pointer in the text file 
        
        # if time out
        except TimeoutError:
            # increment timeout counter
            print("Time out has occurred!")
            total_timeout+=1
            pass

    ########################################
    # END YOUR RDT 3.0 SENDER IMPLEMENTATION HERE #
    ########################################

    # close the socket
    clientSocket.close() 

    # print out your name, the date and time,
    print("DONE sender - {} @ {}".format(name, datetime.datetime.now()))

    # print checksum of the sent file 
    print("File checksum: {}".format(checksum(data[:to_send_size])))
    # print stats
    print("Total packet sent: {}".format(total_packet_sent))
    print("Total packet recv: {}".format(total_packet_recv))
    print("Total corrupted packet recv: {}".format(total_corrupted_pkt_recv))
    print("Total timeout: {}".format(total_timeout))
 
if __name__ == '__main__':
    # check arguments
    if len(sys.argv) != 6:
        print("Expected \"python PA2_sender.py <connection_id> <loss_rate> <corrupt_rate> <max_delay> <transmission_timeout>\"")
        exit()
    connection_ID, loss_rate, corrupt_rate, max_delay, transmission_timeout = sys.argv[1:]
    # start sender
    start_sender(connection_ID, loss_rate, corrupt_rate, max_delay, float(transmission_timeout))