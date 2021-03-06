#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
# Copyright (c) 2020 SUSE LLC.
"""\
Script for benchmarking raid1 read policies. It uses fio on every available
policy for comparison.
"""

import argparse
import logging
import os
import pathlib
import typing

import tabulate

import btrfs
import fio


log = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--debug", help="Verbose debug log",
                        action="store_true")
    parser.add_argument("--fio-job", "-j",
                        help=("Path to the fio job to use. If not set, the "
                              "default pre-defined job will be used."),
                        type=pathlib.Path)
    parser.add_argument("--loops", type=int,
                        help="Number of loops to run fio jobs in")
    parser.add_argument("--size", type=str, default=fio.DEFAULT_SIZE,
                        help="Default size of I/O to test")
    parser.add_argument("mountpoint",
                        help="Mountpoint of the btrfs filesystem to tune",
                        type=pathlib.Path)
    args = parser.parse_args()

    fio.check_prerequisities()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    os.chdir(args.mountpoint)
    fsid = btrfs.get_fsid(args.mountpoint)

    headers = [
        "policy",
        "seqread\n(1 thread)",
        f"seqread\n({os.cpu_count()} threads)",
        "randread\n(1 thread)",
        f"randread\n({os.cpu_count()} threads)",
    ]
    table = []
    for policy in btrfs.get_policies(fsid):
        with btrfs.set_policy(fsid, policy):
            log.debug(f"benchmarking policy: {policy}")
            log.debug("sequential singletreaded")
            bw_seq_single, _, _ = fio.run_fio_pipe(
                fio.job_seqread_singlethread(loops=args.loops, size=args.size),
                to_mibs=True)
            log.debug("sequential multithreaded")
            bw_seq_multi_min, bw_seq_multi_max, bw_seq_multi_sum = \
                fio.run_fio_pipe(
                    fio.job_seqread_multithread(loops=args.loops,
                                                size=args.size),
                    to_mibs=True)
            log.debug("random singlethreaded")
            bw_rand_single, _, _ = fio.run_fio_pipe(
                fio.job_randread_singlethread(loops=args.loops, size=args.size),
                to_mibs=True)
            log.debug("random multithreaded")
            bw_rand_multi_min, bw_rand_multi_max, bw_rand_multi_sum = \
                fio.run_fio_pipe(
                    fio.job_randread_multithread(loops=args.loops,
                                                 size=args.size),
                    to_mibs=True)

            table.append([
                policy,
                # sequential singlethread
                f"{bw_seq_single} MiB/s",
                # sequential multithread
                f"{bw_seq_multi_sum} MiB/s\n"
                f"({bw_seq_multi_min}-{bw_seq_multi_max} MiB/s)",
                # random singlethread
                f"{bw_rand_single} MiB/s",
                # random multithread
                f"{bw_rand_multi_sum} MiB/s\n"
                f"({bw_rand_multi_min}-{bw_rand_multi_max} MiB/s)",
            ])

    print(tabulate.tabulate(table, headers, tablefmt="pretty"))


if __name__ == "__main__":
    main()
