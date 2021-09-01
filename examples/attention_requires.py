#!/usr/bin/env python3
import asab
import os
import asab.api
import time
import asab.zookeeper

from pathlib import Path

###

L = asab.config.logging.getLogger(__name__)


###


class MyApplication(asab.Application):

    def __init__(self):
        super().__init__()

        # Loading the zookeeper service module
        self.add_module(asab.zookeeper.Module)

        # Advertise self thru ZooKeeper
        zksvc = self.get_service("asab.ZooKeeperService")

        svc = asab.api.ApiService(self)

        # get the  zookeeper container
        svc.initialize_zookeeper(zksvc.DefaultContainer)

        # initially set the key to None.
        key1 = None

        print("In attention-required")
        my_key = svc.attention_required(key1)
        current_path = Path(os.path.dirname(os.path.realpath(__file__)))
        key_path = os.path.join(current_path, "data", "my_error_id.txt")

        with open(key_path, 'w') as f:
            f.write(my_key)
        f.close()

        # get the key delete error id
        with open(key_path, 'r') as f:
            get_key = f.read()

        print("In remove attention required")
        print()
        print("Error id created is : " + str(my_key))
        print("Error id being deleted is : " + str(get_key))
        start = time.time()

        while time.time() < start + 10:
            svc.remove_attention(get_key)

        # remove thw key file
        os.remove(key_path)

    print("Done!")


if __name__ == "__main__":
    app = MyApplication()
    app.run()
