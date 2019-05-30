import typing

from bxcommon.messages.bloxroute.compact_block_short_ids_serializer import BlockOffsets
from bxgateway.utils.btc.btc_object_hash import BtcObjectHash


class BlockHeaderInfo(typing.NamedTuple):
    block_offsets: BlockOffsets
    short_ids: typing.List[int]
    short_ids_len: int
    block_hash: BtcObjectHash
    offset: int
    txn_count: int
