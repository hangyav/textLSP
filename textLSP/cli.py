import logging
import argparse

from .server import SERVER


def getArguments():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '-a',
        '--address',
        type=str,
        help='Listen address.'
    )
    parser.add_argument(
        '-p',
        '--port',
        type=int,
        help='Listen port.'
    )
    parser.add_argument(
        '--log-level',
        type=str,
        default='WARNING',
        choices=list(logging._nameToLevel.keys())
    )

    return parser.parse_args()


def main():
    args = getArguments()

    address = args.address
    port = args.port
    log_level = args.log_level.upper()

    logging.basicConfig(level=logging._nameToLevel[log_level])

    if address is not None and port is not None:
        SERVER.start_tcp(address, port)
    else:
        SERVER.start_io()


if __name__ == "__main__":
    main()
