import argparse
import socket
import sys

from utils import PacketHeader, compute_checksum


def send_ack(sock, address, seq):
    ack = PacketHeader(type=3, seq_num=seq, length=0)
    ack.checksum = compute_checksum(ack)
    sock.sendto(bytes(ack), address)


def receiver(receiver_ip, receiver_port, window_size):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((receiver_ip, receiver_port))
    expected = 1
    buffer = {}
    connected = False
    while True:
        pkt, address = s.recvfrom(2048)

        pkt_header = PacketHeader(pkt[:16])
        msg = pkt[16 : 16 + pkt_header.length]

        pkt_checksum = pkt_header.checksum
        pkt_header.checksum = 0
        if pkt_checksum != compute_checksum(pkt_header / msg):
            continue

        if pkt_header.type == 0:
            if not connected:
                connected = True
                expected = 1
                buffer = {}
                send_ack(s, address, 1)

        elif pkt_header.type == 2 and connected:
            seq = pkt_header.seq_num
            if seq >= expected + window_size:
                continue
            if seq >= expected:
                buffer[seq] = msg
            while expected in buffer:
                sys.stdout.buffer.write(buffer.pop(expected))
                expected += 1
            send_ack(s, address, expected)

        elif pkt_header.type == 1 and connected:
            send_ack(s, address, pkt_header.seq_num)
            sys.stdout.buffer.flush()
            break


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "receiver_ip", help="The IP address of the host that receiver is running on"
    )
    parser.add_argument(
        "receiver_port", type=int, help="The port number on which receiver is listening"
    )
    parser.add_argument(
        "window_size", type=int, help="Maximum number of outstanding packets"
    )
    args = parser.parse_args()

    receiver(args.receiver_ip, args.receiver_port, args.window_size)


if __name__ == "__main__":
    main()