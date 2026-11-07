import argparse
import socket
import sys
import time

from utils import PacketHeader, compute_checksum


def make_packet(ptype, seq, payload=b""):
    header = PacketHeader(type=ptype, seq_num=seq, length=len(payload))
    header.checksum = compute_checksum(header / payload)
    return bytes(header / payload)


def wait_ack(sock, timeout):
    sock.settimeout(max(timeout, 0.001))
    try:
        pkt, _ = sock.recvfrom(2048)
    except socket.timeout:
        return None
    header = PacketHeader(pkt[:16])
    received = header.checksum
    header.checksum = 0
    if received != compute_checksum(header / pkt[16 : 16 + header.length]):
        return -1
    if header.type != 3:
        return -1
    return header.seq_num


def sender(receiver_ip, receiver_port, window_size):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    addr = (receiver_ip, receiver_port)

    data = sys.stdin.buffer.read()
    chunks = [data[i : i + 1456] for i in range(0, len(data), 1456)]
    total = len(chunks)

    while True:
        s.sendto(make_packet(0, 0), addr)
        if wait_ack(s, 0.5) == 1:
            break

    base = 1
    next_seq = 1
    acked = set()
    timer = time.time()

    while base <= total:
        while next_seq < base + window_size and next_seq <= total:
            s.sendto(make_packet(2, next_seq, chunks[next_seq - 1]), addr)
            next_seq += 1

        ack = wait_ack(s, 0.5 - (time.time() - timer))

        if ack is None:
            for seq in range(base, next_seq):
                if seq not in acked:
                    s.sendto(make_packet(2, seq, chunks[seq - 1]), addr)
            timer = time.time()
        elif base <= ack < next_seq:
            acked.add(ack)
            if ack == base:
                while base in acked:
                    base += 1
                timer = time.time()

    end_seq = total + 1
    deadline = time.time() + 0.5
    while time.time() < deadline:
        s.sendto(make_packet(1, end_seq), addr)
        remaining = deadline - time.time()
        wait_time = min(0.1, remaining)
        if wait_time <= 0:
            break
        if wait_ack(s, wait_time) == end_seq:
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

    sender(args.receiver_ip, args.receiver_port, args.window_size)


if __name__ == "__main__":
    main()