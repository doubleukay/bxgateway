from mock import MagicMock

from bxcommon.models.bdn_account_model_base import BdnAccountModelBase
from bxcommon.models.bdn_service_model_base import FeedServiceModelBase
from bxcommon.models.bdn_service_model_config_base import BdnFeedServiceModelConfigBase
from bxcommon.rpc.bx_json_rpc_request import BxJsonRpcRequest
from bxcommon.rpc.rpc_errors import RpcInvalidParams, RpcAccountIdError
from bxcommon.rpc.rpc_request_type import RpcRequestType
from bxcommon.test_utils.abstract_test_case import AbstractTestCase
from bxcommon.test_utils.helpers import async_test
from bxcommon.feed.feed import Feed
from bxcommon.feed.feed_manager import FeedManager
from bxcommon.feed import filter_parsing
from bxutils.encoding.json_encoder import Case
from bxutils import logging

from bxgateway.testing import gateway_helpers
from bxgateway.rpc.subscription_rpc_handler import SubscriptionRpcHandler
from bxgateway.testing.mocks.mock_gateway_node import MockGatewayNode

logger = logging.get_logger()


class TestFeed(Feed[str, str]):
    def serialize(self, raw_message: str) -> str:
        return raw_message


class FilterParsingTest(AbstractTestCase):
    def setUp(self) -> None:
        self.gateway = MockGatewayNode(gateway_helpers.get_gateway_opts(8000))
        self.feed_manager = FeedManager(self.gateway)
        self.rpc = SubscriptionRpcHandler(self.gateway, self.feed_manager, Case.SNAKE)

        self.feed_service_model = FeedServiceModelBase(
            allow_filtering=True,
            available_fields=["all"]
        )
        self.base_feed_service_model = BdnFeedServiceModelConfigBase(
            expire_date="2999-01-01",
            feed=self.feed_service_model
        )
        self.gateway.account_model = BdnAccountModelBase(
            account_id="account_id",
            certificate="",
            logical_account_name="test",
            new_transaction_streaming=self.base_feed_service_model,
        )
        self.gateway.account_model.get_feed_service_config_by_name = MagicMock(
            return_value=self.gateway.account_model.new_transaction_streaming
        )

    @async_test
    async def test_subscribe_to_feed_with_filters_all(self):
        feed = TestFeed("bar")
        feed.FILTERS = ["field1", "field2"]

        self.feed_manager.register_feed(feed)
        subscribe_request1 = BxJsonRpcRequest(
            "1", RpcRequestType.SUBSCRIBE, ["bar", {"filters": "field1 == 2"}],
        )

        rpc_handler = self.rpc.get_request_handler(subscribe_request1)
        result = await rpc_handler.process_request()
        self.assertTrue(result)

    @async_test
    async def test_subscribe_to_feed_with_filters2(self):
        feed = TestFeed("bar")
        feed.FILTERS = ["to", "field2"]

        self.feed_manager.register_feed(feed)
        subscribe_request1 = BxJsonRpcRequest(
            "1", RpcRequestType.SUBSCRIBE, ["bar", {"filters": "to = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"}],
        )

        rpc_handler = self.rpc.get_request_handler(subscribe_request1)
        result = await rpc_handler.process_request()
        self.assertTrue(result)

    @async_test
    async def test_subscribe_to_feed_with_invalid_filters(self):
        feed = TestFeed("foo")
        feed.FILTERS = ["filter1", "filter2"]
        self.feed_manager.register_feed(feed)
        subscribe_request1 = BxJsonRpcRequest(
            "1",
            RpcRequestType.SUBSCRIBE,
            ["foo", {"filters": [{"field1": []}, "AND", {"field2": []}]}],
        )

        with self.assertRaises(RpcInvalidParams):
            rpc_handler = self.rpc.get_request_handler(subscribe_request1)
            await rpc_handler.process_request()

        subscribe_request2 = BxJsonRpcRequest(
            "1", RpcRequestType.SUBSCRIBE, ["foo", {"filters": [True, False, 1, 2]}]
        )
        with self.assertRaises(RpcInvalidParams):
            rpc_handler = self.rpc.get_request_handler(subscribe_request2)
            await rpc_handler.process_request()

        subscribe_request3 = BxJsonRpcRequest(
            "1", RpcRequestType.SUBSCRIBE, ["foo", {"filters": {"a": 1}}]
        )
        with self.assertRaises(RpcInvalidParams):
            rpc_handler = self.rpc.get_request_handler(subscribe_request3)
            await rpc_handler.process_request()
        subscribe_request4 = BxJsonRpcRequest(
            "1", RpcRequestType.SUBSCRIBE, ["foo", {"filters": "hello === r and i"}],
        )
        with self.assertRaises(RpcInvalidParams):
            rpc_handler = self.rpc.get_request_handler(subscribe_request4)
            await rpc_handler.process_request()

        subscribe_request4 = BxJsonRpcRequest(
            "1", RpcRequestType.SUBSCRIBE, ["foo", {"filters": "hello > 1"}],
        )
        with self.assertRaises(RpcInvalidParams):
            rpc_handler = self.rpc.get_request_handler(subscribe_request4)
            await rpc_handler.process_request()

    @async_test
    async def test_subscribe_to_feed_with_filtering_not_allowed(self):
        feed_service_model = FeedServiceModelBase(
            allow_filtering=False,
            available_fields=["all"]
        )
        base_feed_service_model = BdnFeedServiceModelConfigBase(
            expire_date="2999-01-01",
            feed=feed_service_model
        )
        self.gateway.account_model.new_transaction_streaming = base_feed_service_model

        self.gateway.account_model.get_feed_service_config_by_name = MagicMock(
            return_value=self.gateway.account_model.new_transaction_streaming
        )

        feed = TestFeed("bar")
        feed.FILTERS = ["to", "field2"]

        self.feed_manager.register_feed(feed)
        subscribe_request1 = BxJsonRpcRequest(
            "1", RpcRequestType.SUBSCRIBE, ["bar", {"filters": "to = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"}],
        )

        with self.assertRaises(RpcAccountIdError):
            rpc_handler = self.rpc.get_request_handler(subscribe_request1)
            await rpc_handler.process_request()

    @async_test
    async def test_filters1(self):
        t2 = "value > 5534673480000000000 or from = 0xbd4e113ee68bcbbf768ba1d6c7a14e003362979a"
        validator = filter_parsing.get_validator(t2)
        self.assertTrue(validator({"value": 6534673480000000000, "from": "a"}))
        self.assertFalse(validator({"value": 50, "from": "a"}))
        self.assertTrue(validator({"value": 50, "from": "0xbd4e113ee68bcbbf768ba1d6c7a14e003362979a"}))

    @async_test
    async def test_filters2(self):
        t2 = "from = 0xbd4e113ee68bcbbf768ba1d6c7a14e003362979a or value > 5534673480000000000"

        f = {"value": 1.3467348e+18, "to": "0xd7bec4d6bf6fc371eb51611a50540f0b59b5f896",
             "from": "0xbd4e113ee68bcbbf768ba1d6c7a14e003362979a"}
        validator = filter_parsing.get_validator(t2)
        self.assertTrue(validator({"value": 6534673480000000000, "from": "a"}))
        self.assertFalse(validator({"value": 50, "from": "a"}))
        self.assertTrue(validator({"value": 50, "from": "0xbd4e113ee68bcbbf768ba1d6c7a14e003362979a"}))
        self.assertTrue(validator(f))

    @async_test
    async def test_filters3(self):
        t3 = "value > 5534673480000000000 or (to = 0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be or to = 0xbd4e113ee68bcbbf768ba1d6c7a14e0033629792)"
        validator = filter_parsing.get_validator(t3)
        f = {"value": 1.3467348e+18, "to": "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be",
             "from": "0xbd4e113ee68bcbbf768ba1d6c7a14e003362979a"}
        self.assertTrue(validator(f))

    @async_test
    async def test_filters4(self):
        t4 = "to = 0x1111111111111111111111111111111111111111 or to = aaaa"
        validator = filter_parsing.get_validator(t4)
        f = {"value": 1.3467348e+18, "to": "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be",
             "from": "0xbd4e113ee68bcbbf768ba1d6c7a14e003362979a"}
        self.assertFalse(validator(f))

    @async_test
    async def test_filters5(self):
        t5 = "gas_price < 100"
        validator = filter_parsing.get_validator(t5)
        f = {"gas_price": 200}
        self.assertFalse(validator(f))

    @async_test
    async def test_filters6(self):
        t6 = "gas_price > 100"
        validator = filter_parsing.get_validator(t6)
        f = {"gas_price": 200}
        self.assertTrue(validator(f))
