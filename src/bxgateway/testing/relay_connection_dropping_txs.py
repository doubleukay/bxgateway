from bxcommon.utils import logger
from bxgateway.connections.relay_connection import RelayConnection


class RelayConnectionDroppingTxs(RelayConnection):
    def __init__(self, sock, address, node, setup=False):
        super(RelayConnectionDroppingTxs, self).__init__(sock, address, node, setup)

        logger.debug("Test mode: Client is started in test mode. Simulating dropped transactions.")

        self.tx_drop_counter = 0
        self.tx_assign_drop_counter = 0
        self.tx_unknown_txs_drop_counter = 0

    def msg_tx(self, msg):

        self.tx_drop_counter += 1

        # Drop every 10th message
        if self.tx_drop_counter > 0 and self.tx_drop_counter % 10 == 0:
            self.tx_drop_counter = 0
            logger.debug("Test mode: Dropping transaction message.")
        else:
            super(RelayConnectionDroppingTxs, self).msg_tx(msg)

    def msg_txassign(self, msg):

        self.tx_assign_drop_counter += 1

        # Drop every 9th message
        if self.tx_assign_drop_counter > 0 and self.tx_assign_drop_counter % 9 == 0:
            self.tx_assign_drop_counter = 0
            logger.debug("Test mode: Dropping transaction assign message.")
        else:
            super(RelayConnectionDroppingTxs, self).msg_txassign(msg)

    def msg_unknown_txs(self, msg):
        self.tx_unknown_txs_drop_counter += 1

        # Drop every 3rd message
        if self.tx_unknown_txs_drop_counter > 0 and self.tx_unknown_txs_drop_counter % 3 == 0:
            self.tx_unknown_txs_drop_counter = 0
            logger.debug("Test mode: Dropping unknown txs message.")
        else:
            super(RelayConnectionDroppingTxs, self).msg_unknown_txs(msg)
