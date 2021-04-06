#!/usr/bin/python3
import saraN210


def main():
    serial = '/dev/tnt1'
    speed = 9600

    lib = saraN210.SARAN210(serial, speed)
    input("Press Enter to Stop ...\n")

    lib.stop_loop()


if __name__ == '__main__':
    main()

