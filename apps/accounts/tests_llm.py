"""
LLM 通信全链路测试
==================
覆盖 chat_context.py、llm_service.py、sse_handler.py 三个模块的单元和集成测试。

测试策略：
- llm_service: 纯逻辑，用 mock 替代外部 LLM 调用
- chat_context: 需要数据库数据，用 django TestCase
- sse_handler: ASGI 层，用 mock receive/send 验证 SSE 协议
"""

import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from .models import User, UserLLMConfig
from .chat_context import build_pve_context
from .llm_service import build_llm, build_langchain_messages, stream_chat

# =============================================================================
# llm_service.py 单元测试
# =============================================================================


class LLMServiceBuildLLMTest(TestCase):
    """build_llm() — 构建 LangChain ChatOpenAI 实例"""

    def setUp(self):
        self.config = UserLLMConfig(
            id=1,
            name="test",
            api_key="sk-test-key",
            base_url="https://api.deepseek.com",
            model="deepseek-v4-pro",
        )

    def test_build_llm_basic(self):
        """基础构建：正确传递 api_key / base_url / model"""
        llm = build_llm(self.config)
        # ChatOpenAI 内部字段通过 pydantic 管理，不直接暴露 .api_key
        # 验证 openai_api_base 和 model_name
        self.assertEqual(llm.model_name, "deepseek-v4-pro")
        self.assertIn("api.deepseek.com", llm.openai_api_base)

    def test_build_llm_base_url_with_v1_suffix(self):
        """base_url 末尾有 /v1 时自动去除"""
        self.config.base_url = "https://api.deepseek.com/v1"
        llm = build_llm(self.config)
        self.assertNotIn("/v1", llm.openai_api_base)
        self.assertIn("api.deepseek.com", llm.openai_api_base)

    def test_build_llm_streaming_enabled(self):
        """streaming=True 始终开启"""
        llm = build_llm(self.config)
        self.assertTrue(llm.streaming)

    def test_build_llm_custom_base_url(self):
        """自定义 base_url 透传"""
        self.config.base_url = "https://custom-gateway.example.com"
        llm = build_llm(self.config)
        self.assertIn("custom-gateway.example.com", llm.openai_api_base)

    def test_build_llm_config_combinations(self):
        """多种配置参数组合"""
        test_cases = [
            ("https://api.deepseek.com", "deepseek-v4-pro", "deepseek"),
            ("https://api.moonshot.cn/v1", "kimi-k3", "moonshot"),
            ("https://open.bigmodel.cn", "glm-5.2", "bigmodel"),
            ("https://api.openai.com", "gpt-4o", "openai"),
            ("https://ollama.local:11434/v1", "llama3", "ollama"),
        ]

        for base_url, model_name, keyword in test_cases:
            config = UserLLMConfig(
                api_key="sk-key",
                base_url=base_url,
                model=model_name,
            )
            llm = build_llm(config)
            self.assertIn(keyword, llm.openai_api_base)
            self.assertEqual(llm.model_name, model_name)

    def test_build_llm_v1_normalized_for_moonshot(self):
        """/v1 后缀被正确移除"""
        config = UserLLMConfig(
            api_key="sk-key",
            base_url="https://api.moonshot.cn/v1",
            model="kimi-k3",
        )
        llm = build_llm(config)
        self.assertNotIn("/v1", llm.openai_api_base)

    # ---- 边界条件 ----

    def test_build_llm_empty_api_key_raises(self):
        """api_key 为空时 ChatOpenAI 抛出 OpenAIError（预期行为）"""
        self.config.api_key = ""
        with self.assertRaises(Exception):
            build_llm(self.config)

    def test_build_llm_no_base_url(self):
        """base_url 为空时使用默认值"""
        self.config.base_url = ""
        llm = build_llm(self.config)
        self.assertIsNotNone(llm)

    def test_build_llm_empty_model(self):
        """model 为空时仍能创建实例"""
        self.config.model = ""
        llm = build_llm(self.config)
        self.assertIsNotNone(llm)

    def test_build_llm_trailing_slash(self):
        """base_url 末尾有 / 时不错误处理（不截断）"""
        self.config.base_url = "https://api.deepseek.com/"
        llm = build_llm(self.config)
        self.assertIsNotNone(llm)

    def test_build_llm_v1_in_path_not_suffix(self):
        """base_url 中包含 /v1/ 但不是后缀时不截断"""
        self.config.base_url = "https://gateway.example.com/api/v1/proxy"
        llm = build_llm(self.config)
        self.assertIsNotNone(llm)


class LLMServiceBuildMessagesTest(TestCase):
    """build_langchain_messages() — 消息转换"""

    def test_build_messages_basic(self):
        """user + assistant + user 三回合"""
        raw = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好，有什么可以帮助？"},
            {"role": "user", "content": "查看节点"},
        ]
        msgs = build_langchain_messages(raw)
        self.assertEqual(len(msgs), 3)
        from langchain_core.messages import HumanMessage, AIMessage
        self.assertIsInstance(msgs[0], HumanMessage)
        self.assertIsInstance(msgs[1], AIMessage)
        self.assertIsInstance(msgs[2], HumanMessage)

    def test_build_messages_with_system(self):
        """system message 在首位"""
        raw = [
            {"role": "system", "content": "你是运维助手"},
            {"role": "user", "content": "查看节点"},
        ]
        msgs = build_langchain_messages(raw)
        from langchain_core.messages import SystemMessage, HumanMessage
        self.assertIsInstance(msgs[0], SystemMessage)
        self.assertIsInstance(msgs[1], HumanMessage)

    def test_build_messages_with_pve_context(self):
        """有 PVE context 时追加到 system message 末尾"""
        raw = [
            {"role": "system", "content": "你是运维助手"},
            {"role": "user", "content": "查看节点"},
        ]
        msgs = build_langchain_messages(raw, pve_context="## 集群概览\n节点数: 3")
        from langchain_core.messages import SystemMessage
        self.assertIsInstance(msgs[0], SystemMessage)
        self.assertIn("集群概览", msgs[0].content)
        self.assertIn("节点数: 3", msgs[0].content)

    def test_build_messages_no_system_inserts_context(self):
        """无 system message 但有 PVE context 时，自动在最前面插入"""
        raw = [
            {"role": "user", "content": "查看节点"},
        ]
        msgs = build_langchain_messages(raw, pve_context="## 集群概览\n节点数: 3")
        from langchain_core.messages import SystemMessage
        self.assertIsInstance(msgs[0], SystemMessage)
        self.assertIn("集群概览", msgs[0].content)

    def test_build_messages_empty_pve_context(self):
        """PVE context 为空时不影响"""
        raw = [{"role": "user", "content": "hi"}]
        msgs = build_langchain_messages(raw, pve_context="")
        self.assertEqual(len(msgs), 1)

    def test_build_messages_unknown_role_ignored(self):
        """未知 role 跳过"""
        raw = [{"role": "unknown", "content": "test"}]
        msgs = build_langchain_messages(raw)
        self.assertEqual(len(msgs), 0)

    # ---- 边界条件 ----

    def test_build_messages_missing_content(self):
        """消息缺少 content 字段时不崩溃"""
        raw = [
            {"role": "user"},
            {"role": "assistant", "content": "你好"},
        ]
        msgs = build_langchain_messages(raw)
        from langchain_core.messages import HumanMessage, AIMessage
        # 第一条 user 消息 content 默认为 ''
        self.assertIsInstance(msgs[0], HumanMessage)
        self.assertEqual(msgs[0].content, "")
        self.assertEqual(len(msgs), 2)

    def test_build_messages_extra_fields(self):
        """消息有额外字段时不影响"""
        raw = [
            {"role": "user", "content": "hi", "extra": "ignored", "timestamp": 123456},
        ]
        msgs = build_langchain_messages(raw)
        self.assertEqual(len(msgs), 1)

    def test_build_messages_empty_list(self):
        """空消息列表"""
        msgs = build_langchain_messages([])
        self.assertEqual(len(msgs), 0)

    def test_build_messages_duplicate_system(self):
        """多个 system message 时 PVE context 只追加到第一个"""
        raw = [
            {"role": "system", "content": "你是助手"},
            {"role": "system", "content": "第二条约束"},
            {"role": "user", "content": "hi"},
        ]
        msgs = build_langchain_messages(raw, pve_context="## 集群概览")
        from langchain_core.messages import SystemMessage
        self.assertIsInstance(msgs[0], SystemMessage)
        self.assertEqual(len(msgs), 3)
        # 只有第一个 system message 追加了 context
        self.assertIn("## 集群概览", msgs[0].content)

    def test_build_messages_alternating_roles(self):
        """交替角色: user → assistant → user → assistant 正确映射"""
        raw = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
        ]
        msgs = build_langchain_messages(raw)
        from langchain_core.messages import HumanMessage, AIMessage
        self.assertIsInstance(msgs[0], HumanMessage)
        self.assertIsInstance(msgs[1], AIMessage)
        self.assertIsInstance(msgs[2], HumanMessage)
        self.assertIsInstance(msgs[3], AIMessage)


class LLMServiceStreamChatTest(TestCase):
    """stream_chat() — 异步流式 token 生成"""

    def _mock_llm(self, astream_generator):
        """创建 mock LLM，astream 为给定异步生成器"""
        mock_llm = AsyncMock()
        mock_llm.astream = astream_generator
        return mock_llm

    def _run(self, llm, messages):
        """运行 stream_chat 并返回 token 列表"""
        async def run():
            tokens = []
            async for t in stream_chat(llm, messages):
                tokens.append(t)
            return tokens
        return asyncio.run(run())

    @patch("apps.accounts.llm_service.ChatOpenAI")
    def test_stream_chat_yields_tokens(self, MockChatOpenAI):
        """astream 返回的 token 被逐个 yield"""
        mock_llm = AsyncMock()
        MockChatOpenAI.return_value = mock_llm

        async def mock_astream(_):
            for token in ["Hello", " ", "World", "!"]:
                chunk = MagicMock()
                chunk.content = token
                yield chunk

        mock_llm.astream = mock_astream

        from langchain_core.messages import HumanMessage
        messages = [HumanMessage(content="test")]

        async def run():
            tokens = []
            async for t in stream_chat(mock_llm, messages):
                tokens.append(t)
            return tokens

        tokens = asyncio.run(run())
        self.assertEqual(tokens, ["Hello", " ", "World", "!"])

    @patch("apps.accounts.llm_service.ChatOpenAI")
    def test_stream_chat_empty_chunks_skipped(self, MockChatOpenAI):
        """content 为空的 chunk 被跳过"""
        mock_llm = AsyncMock()
        MockChatOpenAI.return_value = mock_llm

        async def mock_astream(_):
            for content in ["A", "", "B", "", ""]:
                chunk = MagicMock()
                chunk.content = content
                yield chunk

        mock_llm.astream = mock_astream

        from langchain_core.messages import HumanMessage
        messages = [HumanMessage(content="test")]

        async def run():
            tokens = []
            async for t in stream_chat(mock_llm, messages):
                tokens.append(t)
            return tokens

        tokens = asyncio.run(run())
        self.assertEqual(tokens, ["A", "B"])

    # ---- 大规模流式测试 ----

    @patch("apps.accounts.llm_service.ChatOpenAI")
    def test_stream_chat_large_token_count(self, MockChatOpenAI):
        """大量 token（100 个）逐一 yield，验证无批处理"""
        mock_llm = AsyncMock()
        MockChatOpenAI.return_value = mock_llm

        expected = [f"tok-{i}" for i in range(100)]

        async def mock_astream(_):
            for t in expected:
                chunk = MagicMock()
                chunk.content = t
                yield chunk

        mock_llm.astream = mock_astream

        from langchain_core.messages import HumanMessage
        tokens = self._run(mock_llm, [HumanMessage(content="test")])

        self.assertEqual(len(tokens), 100)
        self.assertEqual(tokens, expected)
        # 验证每个 token 确实被单独 yield
        self.assertEqual(tokens[0], "tok-0")
        self.assertEqual(tokens[50], "tok-50")
        self.assertEqual(tokens[99], "tok-99")

    @patch("apps.accounts.llm_service.ChatOpenAI")
    def test_stream_chat_unicode_chinese(self, MockChatOpenAI):
        """中文字符（多字节 Unicode）正确流式输出"""
        mock_llm = AsyncMock()
        MockChatOpenAI.return_value = mock_llm

        # 模拟用户报告的「回了根据，然后卡了，然后直接输出了全部内容」场景
        # 验证每个中文字符/词单独 yield
        chinese_tokens = ["根据", "当前", "集群", "数据", "，", "节点", "CPU", "使用率", "为", "35%"]

        async def mock_astream(_):
            for t in chinese_tokens:
                chunk = MagicMock()
                chunk.content = t
                yield chunk

        mock_llm.astream = mock_astream

        from langchain_core.messages import HumanMessage
        tokens = self._run(mock_llm, [HumanMessage(content="测试")])

        self.assertEqual(tokens, chinese_tokens)
        # 验证中文字符编码正确
        for t in tokens:
            self.assertIsInstance(t, str)
            self.assertTrue(len(t.encode("utf-8")) > 0)

    @patch("apps.accounts.llm_service.ChatOpenAI")
    def test_stream_chat_mixed_empty_and_content(self, MockChatOpenAI):
        """混合空内容和有效内容的 chunk，只 yield 有效内容"""
        mock_llm = AsyncMock()
        MockChatOpenAI.return_value = mock_llm

        async def mock_astream(_):
            pairs = [("", None), ("Hello", "Hello"), ("", None), (" World", " World"), ("", None)]
            for content, _ in pairs:
                chunk = MagicMock()
                chunk.content = content
                yield chunk

        mock_llm.astream = mock_astream

        from langchain_core.messages import HumanMessage
        tokens = self._run(mock_llm, [HumanMessage(content="test")])

        self.assertEqual(tokens, ["Hello", " World"])

    @patch("apps.accounts.llm_service.ChatOpenAI")
    def test_stream_chat_single_very_long_token(self, MockChatOpenAI):
        """单个 token 包含大量内容（>10KB）"""
        mock_llm = AsyncMock()
        MockChatOpenAI.return_value = mock_llm

        long_text = "A" * 20000

        async def mock_astream(_):
            chunk = MagicMock()
            chunk.content = long_text
            yield chunk

        mock_llm.astream = mock_astream

        from langchain_core.messages import HumanMessage
        tokens = self._run(mock_llm, [HumanMessage(content="test")])

        self.assertEqual(len(tokens), 1)
        self.assertEqual(len(tokens[0]), 20000)

    @patch("apps.accounts.llm_service.ChatOpenAI")
    def test_stream_chat_none_content(self, MockChatOpenAI):
        """chunk.content 为 None 时跳过"""
        mock_llm = AsyncMock()
        MockChatOpenAI.return_value = mock_llm

        async def mock_astream(_):
            for content in [None, "A", None, "B", None]:
                chunk = MagicMock()
                chunk.content = content
                yield chunk

        mock_llm.astream = mock_astream

        from langchain_core.messages import HumanMessage
        tokens = self._run(mock_llm, [HumanMessage(content="test")])

        self.assertEqual(tokens, ["A", "B"])


# =============================================================================
# chat_context.py 单元测试
# =============================================================================


class ChatContextKeywordTest(TestCase):
    """build_pve_context() — 关键词匹配"""

    def setUp(self):
        from apps.clusters.models import Cluster
        from apps.scanner.models import (
            ClusterNode, VM, LXC, Storage,
            NetworkInterface, CephStatus, HAResource,
        )

        self.cluster = Cluster.objects.create(
            name="测试集群",
            agent_token="test-token",
            pve_version="8.2.4",
        )
        now = timezone.now()

        self.node_cpu = ClusterNode.objects.create(
            cluster=self.cluster, node_name="pve-1",
            status="online", cpu_load=0.35,
            memory_total_mb=32000, memory_usage_pct=45.0,
            rootfs_total_gb=500, rootfs_used_gb=200,
            uptime_seconds=86400, ip_address="192.168.1.1",
            scanned_at=now,
        )
        self.node_io = ClusterNode.objects.create(
            cluster=self.cluster, node_name="pve-2",
            status="online", cpu_load=0.10,
            memory_total_mb=64000, memory_usage_pct=30.0,
            rootfs_total_gb=1000, rootfs_used_gb=500,
            uptime_seconds=172800, ip_address="192.168.1.2",
            scanned_at=now,
        )

        self.vm = VM.objects.create(
            node=self.node_cpu, vmid=100, name="ubuntu",
            status="running", cpu_usage=0.5, memory_mb=4096,
            scanned_at=now,
        )

        self.lxc = LXC.objects.create(
            node=self.node_io, vmid=200, name="nginx",
            status="running", cpu_usage=0.3, memory_mb=1024,
            scanned_at=now,
        )

        self.storage = Storage.objects.create(
            node=self.node_cpu, storage_name="local",
            type="dir", total_gb=500, used_gb=300,
            used_fraction=0.6, scanned_at=now,
        )

        self.network = NetworkInterface.objects.create(
            node=self.node_cpu, name="vmbr0",
            type="bridge", address="192.168.1.1",
            speed_mbps=1000, scanned_at=now,
        )

        self.ceph = CephStatus.objects.create(
            cluster=self.cluster, health="HEALTH_OK",
            total_osds=12, up_osds=12, in_osds=12,
            total_space_gb=10000, total_avail_gb=6000,
            pool_count=3, scanned_at=now,
        )

        self.ha = HAResource.objects.create(
            cluster=self.cluster, sid="vm:100",
            resource_type="vm", ha_status="started",
            crm_state="active", ha_group="group1",
            scanned_at=now,
        )

    # ---- 边界场景 ----

    def test_build_pve_context_no_cluster(self):
        """cluster_id 为 None 返回空字符串"""
        result = build_pve_context(None, "查看节点")
        self.assertEqual(result, "")

    def test_build_pve_context_cluster_not_found(self):
        """cluster_id 不存在返回空字符串"""
        result = build_pve_context(99999, "查看节点")
        self.assertEqual(result, "")

    # ---- 摘要始终注入 ----

    def test_build_pve_context_basic_summary(self):
        """始终注入集群摘要"""
        result = build_pve_context(self.cluster.id, "随便聊聊")
        self.assertIn("## 集群概览", result)
        self.assertIn("测试集群", result)
        self.assertIn("PVE 版本: 8.2.4", result)

    # ---- 关键词匹配 ----

    def test_build_pve_context_keyword_nodes(self):
        """关键词 '节点' 匹配 nodes 层"""
        result = build_pve_context(self.cluster.id, "帮我看看节点情况")
        self.assertIn("## 节点状态", result)
        self.assertIn("pve-1", result)
        self.assertIn("pve-2", result)
        self.assertIn("35.0%", result)

    def test_build_pve_context_keyword_cpu(self):
        """关键词 'cpu' 匹配 nodes 层"""
        result = build_pve_context(self.cluster.id, "cpu使用量最高的节点")
        self.assertIn("## 节点状态", result)
        self.assertIn("pve-1", result)
        self.assertIn("35.0%", result)

    def test_build_pve_context_keyword_storage(self):
        """关键词 '存储' 匹配 storage 层 + Ceph"""
        result = build_pve_context(self.cluster.id, "查看存储使用情况")
        self.assertIn("## 存储列表", result)
        self.assertIn("local", result)
        self.assertIn("Ceph", result)

    def test_build_pve_context_keyword_network(self):
        """关键词 '网络' 匹配 network 层"""
        result = build_pve_context(self.cluster.id, "检查网络配置")
        self.assertIn("## 网络接口", result)
        self.assertIn("vmbr0", result)

    def test_build_pve_context_keyword_ha(self):
        """关键词 'ha' 匹配 HA 层"""
        result = build_pve_context(self.cluster.id, "ha资源状态")
        self.assertIn("## HA 高可用资源", result)
        self.assertIn("vm:100", result)

    # ---- 默认行为 ----

    def test_build_pve_context_no_keyword_default(self):
        """无关键词匹配时默认加载 nodes + vms + containers 三层"""
        result = build_pve_context(self.cluster.id, "今天天气不错")
        self.assertIn("## 节点状态", result)
        self.assertIn("## 虚拟机列表", result)
        self.assertIn("## LXC 容器列表", result)
        self.assertNotIn("## 存储列表", result)
        self.assertNotIn("## 网络接口", result)
        self.assertNotIn("## HA 高可用资源", result)

    # ---- 多关键词 ----

    def test_build_pve_context_multi_keywords(self):
        """多个关键词匹配多个层"""
        result = build_pve_context(self.cluster.id, "查看节点和存储")
        self.assertIn("## 集群概览", result)
        self.assertIn("## 节点状态", result)
        self.assertIn("## 存储列表", result)
        self.assertNotIn("## LXC 容器列表", result)

    # ---- 数据格式化 ----

    def test_build_pve_context_formats_cpu_percent(self):
        """CPU 0~1 被格式化为百分比"""
        result = build_pve_context(self.cluster.id, "节点")
        self.assertIn("35.0%", result)
        self.assertIn("10.0%", result)

    def test_build_pve_context_formats_uptime(self):
        """uptime_seconds 被格式化为小时"""
        result = build_pve_context(self.cluster.id, "节点")
        self.assertIn("24h", result)    # 86400s = 24h
        self.assertIn("48h", result)    # 172800s = 48h

    # ---- 扩展关键词匹配 ----

    def test_build_pve_context_keyword_sdn(self):
        """关键词 'sdn' 匹配 network 层（含 SDN 数据）"""
        from apps.scanner.models import SDNZone
        SDNZone.objects.create(
            cluster=self.cluster, zone="zone1",
            zone_type="vlan", nodes="pve-1",
            scanned_at=timezone.now(),
        )
        result = build_pve_context(self.cluster.id, "sdn配置情况")
        self.assertIn("## 网络接口", result)
        self.assertIn("SDN", result)

    def test_build_pve_context_keyword_vnet(self):
        """关键词 'vlan' 匹配 network 层"""
        result = build_pve_context(self.cluster.id, "vlan配置")
        self.assertIn("## 网络接口", result)

    def test_build_pve_context_keyword_vm(self):
        """关键词 'vm' 匹配 vms 层"""
        result = build_pve_context(self.cluster.id, "vm状态")
        self.assertIn("## 虚拟机列表", result)
        self.assertIn("ubuntu", result)

    def test_build_pve_context_keyword_container(self):
        """关键词 'container' 匹配 containers 层"""
        result = build_pve_context(self.cluster.id, "container资源")
        self.assertIn("## LXC 容器列表", result)
        self.assertIn("nginx", result)

    def test_build_pve_context_keyword_ip(self):
        """关键词 'ip' 匹配 network 层"""
        result = build_pve_context(self.cluster.id, "查看ip地址")
        self.assertIn("## 网络接口", result)

    def test_build_pve_context_keyword_disk(self):
        """关键词 '磁盘' 匹配 nodes 层（disk 在 nodes 关键词中）"""
        result = build_pve_context(self.cluster.id, "磁盘使用情况")
        self.assertIn("## 节点状态", result)
        # 磁盘不匹配 storage 层（storage 层关键词含 '磁盘容量' 而非 '磁盘'）
        self.assertNotIn("## 存储列表", result)

    # ---- 边界条件 ----

    def test_build_pve_context_empty_message(self):
        """空字符串消息 → 无关键词匹配 → 默认加载三层"""
        result = build_pve_context(self.cluster.id, "")
        self.assertIn("## 集群概览", result)
        self.assertIn("## 节点状态", result)
        self.assertIn("## 虚拟机列表", result)
        self.assertIn("## LXC 容器列表", result)

    def test_build_pve_context_spaces_message(self):
        """空格消息 → 无关键词匹配 → 默认加载三层"""
        result = build_pve_context(self.cluster.id, "   ")
        self.assertIn("## 集群概览", result)
        self.assertIn("## 节点状态", result)
        self.assertIn("## 虚拟机列表", result)

    def test_build_pve_context_cluster_with_no_data(self):
        """集群存在但无扫描数据 → 只返回摘要"""
        from apps.clusters.models import Cluster
        empty_cluster = Cluster.objects.create(name="空集群", agent_token="empty")
        result = build_pve_context(empty_cluster.id, "节点")
        self.assertIn("## 集群概览", result)
        # 没有节点数据
        self.assertNotIn("## 节点状态", result)

    def test_build_pve_context_all_keywords_single_message(self):
        """一条消息匹配所有关键词 → 所有层都加载"""
        result = build_pve_context(
            self.cluster.id,
            "节点cpu内存负载磁盘存储网络sdn接口ha高可用虚拟机容器",
        )
        self.assertIn("## 节点状态", result)
        self.assertIn("## 虚拟机列表", result)
        self.assertIn("## LXC 容器列表", result)
        self.assertIn("## 存储列表", result)
        self.assertIn("## 网络接口", result)
        self.assertIn("## HA 高可用资源", result)

    def test_build_pve_context_mixed_case_keywords(self):
        """关键词大小写混写仍然匹配"""
        result = build_pve_context(self.cluster.id, "CPU和HA")
        self.assertIn("## 节点状态", result)
        self.assertIn("## HA 高可用资源", result)

    def test_build_pve_context_keyword_boundary(self):
        """关键词在单词边界正常匹配（'节点间' 应匹配 nodes 层，因为包含'节点'）"""
        result = build_pve_context(self.cluster.id, "节点间通信")
        self.assertIn("## 节点状态", result)

    def test_build_pve_context_numeric_message(self):
        """纯数字消息 → 无关键词 → 默认三层"""
        result = build_pve_context(self.cluster.id, "12345")
        self.assertIn("## 节点状态", result)
        self.assertIn("## 虚拟机列表", result)


# =============================================================================
# sse_handler.py 集成测试
# =============================================================================


class SSEHandlerAuthTest(TransactionTestCase):
    """sse_chat_stream() — 认证与参数校验层"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="sseuser",
            email="sse@example.com",
            password="TestPass123!",
        )
        # 预创建一个有 API key 的配置
        self.config = UserLLMConfig.objects.create(
            user=self.user, name="test",
            api_key="sk-test-key", provider="deepseek",
            model="deepseek-v4-pro", base_url="https://api.deepseek.com",
        )

    def _make_scope(self, method="POST", auth_header=None):
        scope = {
            "type": "http",
            "method": method,
            "path": "/api/auth/chat/stream/",
            "headers": [],
            "query_string": b"",
        }
        if auth_header:
            scope["headers"].append([b"authorization", auth_header.encode()])
        return scope

    @staticmethod
    def _make_send_collector():
        sent = []
        async def send(message):
            sent.append(message)
        return sent, send

    def _make_receive(self, conf_id=1, has_message=True):
        """返回 mock receive，构造有效 body 使 parse 和 param 校验通过。
        第一次调用返回请求体，后续调用返回 disconnect 避免阻塞。"""
        body_data = {
            "config_id": conf_id,
            "messages": [{"role": "user", "content": "hi"}] if has_message else [],
            "user_message": "hi",
            "cluster_id": None,
        }
        first_call = [True]

        async def receive():
            if first_call[0]:
                first_call[0] = False
                return {
                    "type": "http.request",
                    "body": json.dumps(body_data).encode(),
                    "more_body": False,
                }
            return {"type": "http.disconnect"}

        return receive

    def test_missing_auth(self):
        """无 Authorization 头返回 401"""
        from config.sse_handler import sse_chat_stream
        scope = self._make_scope()
        sent, send = self._make_send_collector()
        receive = self._make_receive(conf_id=1)

        asyncio.run(sse_chat_stream(scope, receive, send))

        start_msgs = [m for m in sent if m["type"] == "http.response.start"]
        self.assertEqual(len(start_msgs), 1)
        self.assertEqual(start_msgs[0]["status"], 401)

    def test_invalid_token(self):
        """无效 JWT token 返回 401"""
        from config.sse_handler import sse_chat_stream
        scope = self._make_scope(auth_header="Bearer invalid-token-xyz")
        sent, send = self._make_send_collector()
        receive = self._make_receive(conf_id=1)

        asyncio.run(sse_chat_stream(scope, receive, send))

        start_msgs = [m for m in sent if m["type"] == "http.response.start"]
        self.assertEqual(len(start_msgs), 1)
        self.assertEqual(start_msgs[0]["status"], 401)

    def test_config_not_found(self):
        """配置不存在返回 404"""
        from rest_framework_simplejwt.tokens import RefreshToken
        token = str(RefreshToken.for_user(self.user).access_token)

        from config.sse_handler import sse_chat_stream
        scope = self._make_scope(auth_header=f"Bearer {token}")
        sent, send = self._make_send_collector()
        receive = self._make_receive(conf_id=99999)

        asyncio.run(sse_chat_stream(scope, receive, send))

        start_msgs = [m for m in sent if m["type"] == "http.response.start"]
        self.assertEqual(start_msgs[0]["status"], 404)

    def test_no_api_key(self):
        """配置无 API key 返回 400"""
        from rest_framework_simplejwt.tokens import RefreshToken
        token = str(RefreshToken.for_user(self.user).access_token)

        # 创建无 key 的配置
        empty_config = UserLLMConfig.objects.create(
            user=self.user, name="no-key", provider="deepseek",
            model="deepseek-v4-pro", base_url="https://api.deepseek.com",
        )

        from config.sse_handler import sse_chat_stream
        scope = self._make_scope(auth_header=f"Bearer {token}")
        sent, send = self._make_send_collector()
        receive = self._make_receive(conf_id=empty_config.id)

        asyncio.run(sse_chat_stream(scope, receive, send))

        start_msgs = [m for m in sent if m["type"] == "http.response.start"]
        self.assertEqual(start_msgs[0]["status"], 400)

    def test_missing_params(self):
        """messages 为空列表时返回 400"""
        from rest_framework_simplejwt.tokens import RefreshToken
        token = str(RefreshToken.for_user(self.user).access_token)

        from config.sse_handler import sse_chat_stream
        scope = self._make_scope(auth_header=f"Bearer {token}")
        sent, send = self._make_send_collector()
        # messages=[] → param check fails
        receive = self._make_receive(conf_id=1, has_message=False)

        asyncio.run(sse_chat_stream(scope, receive, send))

        start_msgs = [m for m in sent if m["type"] == "http.response.start"]
        self.assertEqual(start_msgs[0]["status"], 400)

    def test_rejects_get(self):
        """非 POST 方法返回 405"""
        from config.sse_handler import sse_chat_stream
        scope = self._make_scope(method="GET")
        sent, send = self._make_send_collector()
        receive = self._make_receive(conf_id=1)

        asyncio.run(sse_chat_stream(scope, receive, send))

        start_msgs = [m for m in sent if m["type"] == "http.response.start"]
        self.assertEqual(start_msgs[0]["status"], 405)

    # ---- 请求体校验 ----

    def test_invalid_json_body(self):
        """发送非 JSON 正文返回 400"""
        from config.sse_handler import sse_chat_stream
        scope = self._make_scope()
        sent, send = self._make_send_collector()

        async def receive():
            return {
                "type": "http.request",
                "body": b"not-json-at-all{{{",
                "more_body": False,
            }

        asyncio.run(sse_chat_stream(scope, receive, send))

        start_msgs = [m for m in sent if m["type"] == "http.response.start"]
        self.assertEqual(start_msgs[0]["status"], 400)

    def test_missing_config_id(self):
        """缺少 config_id 返回 400"""
        from rest_framework_simplejwt.tokens import RefreshToken
        token = str(RefreshToken.for_user(self.user).access_token)

        from config.sse_handler import sse_chat_stream
        scope = self._make_scope(auth_header=f"Bearer {token}")
        sent, send = self._make_send_collector()

        async def receive():
            return {
                "type": "http.request",
                "body": json.dumps({
                    "messages": [{"role": "user", "content": "hi"}],
                    "user_message": "hi",
                }).encode(),
                "more_body": False,
            }

        asyncio.run(sse_chat_stream(scope, receive, send))

        start_msgs = [m for m in sent if m["type"] == "http.response.start"]
        self.assertEqual(start_msgs[0]["status"], 400)

    def test_missing_messages_key(self):
        """缺少 messages 字段返回 400"""
        from rest_framework_simplejwt.tokens import RefreshToken
        token = str(RefreshToken.for_user(self.user).access_token)

        from config.sse_handler import sse_chat_stream
        scope = self._make_scope(auth_header=f"Bearer {token}")
        sent, send = self._make_send_collector()

        async def receive():
            return {
                "type": "http.request",
                "body": json.dumps({
                    "config_id": self.config.id,
                    "user_message": "hi",
                }).encode(),
                "more_body": False,
            }

        asyncio.run(sse_chat_stream(scope, receive, send))

        start_msgs = [m for m in sent if m["type"] == "http.response.start"]
        self.assertEqual(start_msgs[0]["status"], 400)

    def test_disconnect_before_body(self):
        """客户端在发送 body 前断连"""
        from config.sse_handler import sse_chat_stream

        class DisconnectFirst:
            def __init__(self):
                self.called = False
            async def receive(self):
                if not self.called:
                    self.called = True
                    return {"type": "http.disconnect"}
                return {"type": "http.disconnect"}

        scope = self._make_scope()
        sent, send = self._make_send_collector()
        df = DisconnectFirst()

        asyncio.run(sse_chat_stream(scope, df.receive, send))

        # 应该静默退出，没有任何响应
        self.assertEqual(len(sent), 0)


class SSEHandlerStreamingTest(TransactionTestCase):
    """sse_chat_stream() — 流式行为"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="streamuser",
            email="stream@example.com",
            password="TestPass123!",
        )
        self.config = UserLLMConfig.objects.create(
            user=self.user, name="test",
            api_key="sk-test-key", provider="deepseek",
            model="deepseek-v4-pro", base_url="https://api.deepseek.com",
        )

    def _make_token(self):
        from rest_framework_simplejwt.tokens import RefreshToken
        return str(RefreshToken.for_user(self.user).access_token)

    def _make_scope(self):
        return {
            "type": "http",
            "method": "POST",
            "path": "/api/auth/chat/stream/",
            "headers": [[b"authorization", f"Bearer {self._make_token()}".encode()]],
            "query_string": b"",
        }

    @staticmethod
    def _make_send_collector():
        sent = []
        async def send(message):
            sent.append(message)
        return sent, send

    def _make_receive_extra(self, extra_body=None):
        """带额外字段的 receive。第一次调用返回请求体，后续返回 disconnect。"""
        body_data = {
            "config_id": self.config.id,
            "messages": [{"role": "user", "content": "hi"}],
            "user_message": "hi",
            **(extra_body or {}),
        }
        first_call = [True]

        async def receive():
            if first_call[0]:
                first_call[0] = False
                return {
                    "type": "http.request",
                    "body": json.dumps(body_data).encode(),
                    "more_body": False,
                }
            return {"type": "http.disconnect"}

        return receive

    @patch("apps.accounts.llm_service.stream_chat")
    def test_sse_format(self, mock_stream_chat):
        """SSE 输出格式正确：data: {...} + [DONE]"""
        async def mock_stream(_llm, _msgs):
            yield "Hello"

        mock_stream_chat.side_effect = mock_stream

        from config.sse_handler import sse_chat_stream
        scope = self._make_scope()
        sent, send = self._make_send_collector()
        receive = self._make_receive_extra()

        asyncio.run(sse_chat_stream(scope, receive, send))

        # 响应头
        start_msgs = [m for m in sent if m["type"] == "http.response.start"]
        self.assertEqual(start_msgs[0]["status"], 200)
        headers = dict(start_msgs[0]["headers"])
        self.assertEqual(headers[b"content-type"], b"text/event-stream")
        self.assertEqual(headers[b"cache-control"], b"no-cache, no-store, must-revalidate")
        self.assertEqual(headers[b"x-accel-buffering"], b"no")

        # SSE body 格式
        body_text = b"".join(
            m["body"] for m in sent if m["type"] == "http.response.body" and m["body"]
        ).decode()
        self.assertIn("data: ", body_text)
        self.assertIn("[DONE]", body_text)
        self.assertIn("Hello", body_text)

    @patch("apps.accounts.llm_service.stream_chat")
    def test_streams_multiple_tokens(self, mock_stream_chat):
        """多个 token 逐个发送"""
        tokens_sent = ["A", "B", "C"]

        async def mock_stream(_llm, _msgs):
            for t in tokens_sent:
                yield t

        mock_stream_chat.side_effect = mock_stream

        from config.sse_handler import sse_chat_stream
        scope = self._make_scope()
        sent, send = self._make_send_collector()
        receive = self._make_receive_extra()

        asyncio.run(sse_chat_stream(scope, receive, send))

        body_text = b"".join(
            m["body"] for m in sent if m["type"] == "http.response.body" and m["body"]
        ).decode()

        for token in tokens_sent:
            self.assertIn(token, body_text)

        # more_body=True 的帧数 >= token 数
        non_final = [m for m in sent if m["type"] == "http.response.body" and m.get("more_body", False)]
        self.assertGreaterEqual(len(non_final), len(tokens_sent))

    @patch("apps.accounts.llm_service.stream_chat")
    def test_handles_llm_error(self, mock_stream_chat):
        """LLM 异常时发送错误消息 + [DONE]"""
        # stream_chat 直接抛出异常（不是 async generator 中抛）
        mock_stream_chat.side_effect = RuntimeError("API timeout")

        from config.sse_handler import sse_chat_stream
        scope = self._make_scope()
        sent, send = self._make_send_collector()
        receive = self._make_receive_extra()

        asyncio.run(sse_chat_stream(scope, receive, send))

        body_text = b"".join(
            m["body"] for m in sent if m["type"] == "http.response.body" and m["body"]
        ).decode()
        self.assertIn("错误", body_text)
        self.assertIn("[DONE]", body_text)

        # 最后一帧 more_body=False
        final_body = [m for m in sent if m["type"] == "http.response.body"][-1]
        self.assertFalse(final_body.get("more_body", True))

    @patch("apps.accounts.llm_service.stream_chat")
    def test_handles_disconnect(self, mock_stream_chat):
        """客户端断连时正常终止"""
        async def mock_stream(_llm, _msgs):
            yield "A"
            yield "B"

        mock_stream_chat.side_effect = mock_stream

        from config.sse_handler import sse_chat_stream
        scope = self._make_scope()
        sent, send = self._make_send_collector()

        # 模拟客户端断连（第一次 receive 返回 body，后续返回 disconnect）
        first_call = [True]

        async def receive_with_disconnect():
            if first_call[0]:
                first_call[0] = False
                return {
                    "type": "http.request",
                    "body": json.dumps({
                        "config_id": self.config.id,
                        "messages": [{"role": "user", "content": "hi"}],
                        "user_message": "hi",
                    }).encode(),
                    "more_body": False,
                }
            return {"type": "http.disconnect"}

        asyncio.run(sse_chat_stream(scope, receive_with_disconnect, send))

        body_text = b"".join(
            m["body"] for m in sent if m["type"] == "http.response.body" and m["body"]
        ).decode()
        self.assertIn("[DONE]", body_text)

    @patch("apps.accounts.chat_context.build_pve_context")
    @patch("apps.accounts.llm_service.stream_chat")
    def test_injects_pve_context(self, mock_stream_chat, mock_build_pve_context):
        """cluster_id 传入时 build_pve_context 被调用"""
        mock_build_pve_context.return_value = "## 集群概览\n节点数: 3"

        async def mock_stream(_llm, _msgs):
            yield "OK"

        mock_stream_chat.side_effect = mock_stream

        from config.sse_handler import sse_chat_stream
        scope = self._make_scope()
        sent, send = self._make_send_collector()
        receive = self._make_receive_extra({"cluster_id": 1, "user_message": "查看节点"})

        asyncio.run(sse_chat_stream(scope, receive, send))

        mock_build_pve_context.assert_called_once_with(1, "查看节点")

    # ========== SEE 流式行为核心测试 ==========

    @patch("apps.accounts.llm_service.stream_chat")
    def test_each_token_is_separate_sse_frame(self, mock_stream_chat):
        """
        核心测试：验证每个 token 对应一个独立的 more_body=True 帧。
        这是防止「回了根据，然后卡了，然后直接输出了全部内容」的关键检查。
        """
        tokens = ["根据", "当前", "数据", "分析", "如下"]

        async def mock_stream(_llm, _msgs):
            for t in tokens:
                yield t

        mock_stream_chat.side_effect = mock_stream

        from config.sse_handler import sse_chat_stream
        scope = self._make_scope()
        sent, send = self._make_send_collector()
        receive = self._make_receive_extra()

        asyncio.run(sse_chat_stream(scope, receive, send))

        # 收集所有 more_body=True 的帧（流式中间帧）
        body_frames = [
            m for m in sent
            if m["type"] == "http.response.body" and m.get("more_body") is True and m["body"]
        ]

        # 每个 token 对应一个帧（排除 connected 消息 ": connected\\n\\n"）
        token_frames = [
            f for f in body_frames
            if f["body"].startswith(b"data: ")
        ]

        # 关键断言：帧数 == token 数（无批处理）
        self.assertEqual(
            len(token_frames), len(tokens),
            f"预期 {len(tokens)} 个 SSE 帧，实际 {len(token_frames)} 个。"
            f"如果帧数少于 token 数，说明发生了批处理缓冲。"
        )

        # 验证每个帧包含对应的 token 内容
        for i, token in enumerate(tokens):
            frame_body = token_frames[i]["body"].decode()
            self.assertIn(token, frame_body,
                          f"第 {i} 个帧应包含 token '{token}'")

    @patch("apps.accounts.llm_service.stream_chat")
    def test_sse_frame_body_is_valid_json(self, mock_stream_chat):
        """每个 SSE data: 行的 JSON body 格式正确"""
        async def mock_stream(_llm, _msgs):
            yield "Hello"

        mock_stream_chat.side_effect = mock_stream

        from config.sse_handler import sse_chat_stream
        scope = self._make_scope()
        sent, send = self._make_send_collector()
        receive = self._make_receive_extra()

        asyncio.run(sse_chat_stream(scope, receive, send))

        for msg in sent:
            if msg["type"] != "http.response.body":
                continue
            body = msg["body"]
            if not body or not body.startswith(b"data: "):
                continue
            data_line = body.decode().strip()
            # 跳过 [DONE] 结束标记
            if data_line.strip().endswith("[DONE]"):
                continue
            # data: {...}
            json_str = data_line[len("data: "):]
            parsed = json.loads(json_str)
            self.assertIn("choices", parsed)
            self.assertEqual(len(parsed["choices"]), 1)
            self.assertIn("delta", parsed["choices"][0])
            self.assertIn("content", parsed["choices"][0]["delta"])

    @patch("apps.accounts.llm_service.stream_chat")
    def test_ordered_sse_sequence(self, mock_stream_chat):
        """SSE 序列顺序： connected → token data → [DONE]"""
        async def mock_stream(_llm, _msgs):
            yield "A"
            yield "B"

        mock_stream_chat.side_effect = mock_stream

        from config.sse_handler import sse_chat_stream
        scope = self._make_scope()
        sent, send = self._make_send_collector()
        receive = self._make_receive_extra()

        asyncio.run(sse_chat_stream(scope, receive, send))

        # 提取 body 帧的顺序列表
        body_sequence = [
            m["body"] for m in sent
            if m["type"] == "http.response.body" and m["body"]
        ]

        # 第一个帧应该是 ": connected\\n\\n"
        self.assertTrue(
            body_sequence[0].startswith(b": connected"),
            f"第一帧应为 connected 消息，实际: {body_sequence[0][:50]}"
        )

        # 最后一个帧应该是 [DONE]
        self.assertTrue(
            body_sequence[-1].startswith(b"data: [DONE]"),
            f"最后一帧应为 [DONE]，实际: {body_sequence[-1][:50]}"
        )

        # 中间帧是 token data
        for i in range(1, len(body_sequence) - 1):
            self.assertTrue(
                body_sequence[i].startswith(b"data: "),
                f"中间帧 {i} 应为 data: 格式"
            )

    @patch("apps.accounts.llm_service.stream_chat")
    def test_final_frame_more_body_false(self, mock_stream_chat):
        """最后一个 [DONE] 帧的 more_body=False"""
        async def mock_stream(_llm, _msgs):
            yield "A"

        mock_stream_chat.side_effect = mock_stream

        from config.sse_handler import sse_chat_stream
        scope = self._make_scope()
        sent, send = self._make_send_collector()
        receive = self._make_receive_extra()

        asyncio.run(sse_chat_stream(scope, receive, send))

        body_msgs = [m for m in sent if m["type"] == "http.response.body"]
        self.assertGreater(len(body_msgs), 0)
        # 最后一个 body 消息的 more_body 应为 False
        final = body_msgs[-1]
        self.assertFalse(final.get("more_body", True))

    @patch("apps.accounts.llm_service.stream_chat")
    def test_empty_stream_no_tokens(self, mock_stream_chat):
        """stream_chat 不 yield 任何 token → 只发送 connected + [DONE]"""
        async def mock_stream(_llm, _msgs):
            # 空生成器
            return
            yield  # pragma: no cover

        mock_stream_chat.side_effect = mock_stream

        from config.sse_handler import sse_chat_stream
        scope = self._make_scope()
        sent, send = self._make_send_collector()
        receive = self._make_receive_extra()

        asyncio.run(sse_chat_stream(scope, receive, send))

        body_text = b"".join(
            m["body"] for m in sent if m["type"] == "http.response.body" and m["body"]
        ).decode()
        self.assertIn("[DONE]", body_text)

    @patch("apps.accounts.llm_service.stream_chat")
    def test_error_after_partial_tokens(self, mock_stream_chat):
        """stream 在 yield 部分 token 后抛出异常"""
        tokens_sent_before_error = []

        async def mock_stream(_llm, _msgs):
            nonlocal tokens_sent_before_error
            tokens_sent_before_error.append("AA")
            yield "AA"
            tokens_sent_before_error.append("BB")
            yield "BB"
            raise RuntimeError("mid-stream error")

        mock_stream_chat.side_effect = mock_stream

        from config.sse_handler import sse_chat_stream
        scope = self._make_scope()
        sent, send = self._make_send_collector()
        receive = self._make_receive_extra()

        asyncio.run(sse_chat_stream(scope, receive, send))

        body_text = b"".join(
            m["body"] for m in sent if m["type"] == "http.response.body" and m["body"]
        ).decode()

        # 已收到的 token 应该已发出
        self.assertIn("AA", body_text)
        self.assertIn("BB", body_text)
        # 错误消息应该已发出
        self.assertIn("错误", body_text)
        self.assertIn("mid-stream error", body_text)
        # [DONE] 应该已发出
        self.assertIn("[DONE]", body_text)

    @patch("apps.accounts.llm_service.stream_chat")
    def test_disconnect_after_first_token(self, mock_stream_chat):
        """客户端在收到第一个 token 后断连"""
        async def mock_stream(_llm, _msgs):
            yield "token1"
            yield "token2"

        mock_stream_chat.side_effect = mock_stream

        from config.sse_handler import sse_chat_stream
        scope = self._make_scope()
        sent, send = self._make_send_collector()

        # 模拟：body 请求后第一次 receive 返回请求，之后收到 disconnect
        recv_count = [0]

        async def receive():
            recv_count[0] += 1
            if recv_count[0] == 1:
                return {
                    "type": "http.request",
                    "body": json.dumps({
                        "config_id": self.config.id,
                        "messages": [{"role": "user", "content": "hi"}],
                        "user_message": "hi",
                    }).encode(),
                    "more_body": False,
                }
            return {"type": "http.disconnect"}

        asyncio.run(sse_chat_stream(scope, receive, send))

        body_text = b"".join(
            m["body"] for m in sent if m["type"] == "http.response.body" and m["body"]
        ).decode()

        # 至少第一个 token 已发出
        self.assertIn("token1", body_text)
        # [DONE] 已发送（保证 chunked 编码正常结束）
        self.assertIn("[DONE]", body_text)

    @patch("apps.accounts.llm_service.stream_chat")
    def test_large_token_in_sse(self, mock_stream_chat):
        """单 token 包含大规模内容（>10KB）在 SSE 中正确传输"""
        large_content = "X" * 15000

        async def mock_stream(_llm, _msgs):
            yield large_content

        mock_stream_chat.side_effect = mock_stream

        from config.sse_handler import sse_chat_stream
        scope = self._make_scope()
        sent, send = self._make_send_collector()
        receive = self._make_receive_extra()

        asyncio.run(sse_chat_stream(scope, receive, send))

        body_text = b"".join(
            m["body"] for m in sent if m["type"] == "http.response.body" and m["body"]
        ).decode()
        self.assertIn(large_content, body_text)


# =============================================================================
# 全链路集成测试
# =============================================================================


class FullLLMIntegrationTest(TransactionTestCase):
    """
    组合测试：验证 llm_service 和 chat_context 在多个配置和关键词组合下的行为。
    """

    def setUp(self):
        from apps.clusters.models import Cluster
        from apps.scanner.models import (
            ClusterNode, VM, LXC,
            Storage, NetworkInterface, HAResource,
        )

        self.user = User.objects.create_user(
            username="fulltest", email="full@example.com",
            password="TestPass123!",
        )
        self.cluster = Cluster.objects.create(
            name="全链路集群", agent_token="test-token",
        )
        now = timezone.now()

        self.node = ClusterNode.objects.create(
            cluster=self.cluster, node_name="fullnode",
            status="online", cpu_load=0.50, memory_total_mb=16000,
            memory_usage_pct=60.0, rootfs_total_gb=200, rootfs_used_gb=150,
            uptime_seconds=3600, ip_address="10.0.0.1", scanned_at=now,
        )
        VM.objects.create(
            node=self.node, vmid=101, name="web-server",
            status="running", cpu_usage=0.75, memory_mb=8192, scanned_at=now,
        )
        LXC.objects.create(
            node=self.node, vmid=201, name="redis-cache",
            status="running", cpu_usage=0.20, memory_mb=512, scanned_at=now,
        )
        Storage.objects.create(
            node=self.node, storage_name="ceph-pool", type="rbd",
            total_gb=5000, used_gb=3000, used_fraction=0.6, scanned_at=now,
        )
        NetworkInterface.objects.create(
            node=self.node, name="bond0", type="bond",
            address="10.0.0.1", speed_mbps=10000, scanned_at=now,
        )
        HAResource.objects.create(
            cluster=self.cluster, sid="vm:101", resource_type="vm",
            ha_status="started", crm_state="active", scanned_at=now,
        )

        self.config = UserLLMConfig.objects.create(
            user=self.user, name="test", api_key="sk-test-key",
            provider="deepseek", model="deepseek-v4-pro",
            base_url="https://api.deepseek.com",
        )

    def _assert_layers_present(self, result, expected_layers, unexpected_layers):
        """辅助断言：检查 context 中各层是否出现"""
        section_names = {
            "nodes": "## 节点状态",
            "vms": "## 虚拟机列表",
            "containers": "## LXC 容器列表",
            "storage": "## 存储列表",
            "network": "## 网络接口",
            "ha": "## HA 高可用资源",
        }
        for layer in expected_layers:
            self.assertIn(section_names[layer], result,
                          f"层 '{layer}' 应出现但未出现")
        for layer in unexpected_layers:
            self.assertNotIn(section_names[layer], result,
                             f"层 '{layer}' 不应出现但出现了")

    def test_chat_context_full_keywords(self):
        """全关键词 → 所有数据层都注入"""
        result = build_pve_context(
            self.cluster.id,
            "节点、虚拟机、容器、存储、网络、ha全看",
        )
        self._assert_layers_present(result,
            ["nodes", "vms", "containers", "storage", "network", "ha"],
            [])

    def test_chat_context_storage_and_ha_only(self):
        """只匹配存储和 HA → 只注入这两层"""
        result = build_pve_context(self.cluster.id, "存储池和ha高可用状态")
        self._assert_layers_present(result,
            ["storage", "ha"],
            ["nodes", "vms", "containers", "network"])

    def test_chat_context_vm_containers_network(self):
        """匹配 VM、容器、网络 → 注入这三层"""
        result = build_pve_context(self.cluster.id, "虚拟机和容器的网络配置")
        self._assert_layers_present(result,
            ["vms", "containers", "network"],
            ["nodes", "storage", "ha"])

    def test_langchain_messages_with_full_pve_context(self):
        """LLM 消息 + 完整 PVE context 正确组装"""
        raw = [
            {"role": "system", "content": "你是运维助手"},
            {"role": "user", "content": "全链路测试"},
        ]
        pve_ctx = build_pve_context(self.cluster.id, "节点、虚拟机、容器")
        msgs = build_langchain_messages(raw, pve_context=pve_ctx)
        self.assertGreater(len(msgs), 0)
        from langchain_core.messages import SystemMessage
        self.assertIsInstance(msgs[0], SystemMessage)
        self.assertIn("全链路集群", msgs[0].content)
        self.assertIn("web-server", msgs[0].content)
        self.assertIn("redis-cache", msgs[0].content)

    def test_sse_handler_with_pve_config(self):
        """sse_handler + 有 API key 的配置 + 有效 token = 200"""
        from rest_framework_simplejwt.tokens import RefreshToken
        token = str(RefreshToken.for_user(self.user).access_token)

        from config.sse_handler import sse_chat_stream
        scope = {
            "type": "http", "method": "POST",
            "path": "/api/auth/chat/stream/",
            "headers": [[b"authorization", f"Bearer {token}".encode()]],
            "query_string": b"",
        }
        sent, send = SSEHandlerAuthTest._make_send_collector()
        first_call = [True]

        async def receive():
            if first_call[0]:
                first_call[0] = False
                return {
                    "type": "http.request",
                    "body": json.dumps({
                        "config_id": self.config.id,
                        "messages": [{"role": "user", "content": "hi"}],
                        "user_message": "hi",
                        "cluster_id": self.cluster.id,
                    }).encode(),
                    "more_body": False,
                }
            return {"type": "http.disconnect"}

        asyncio.run(sse_chat_stream(scope, receive, send))

        start_msgs = [m for m in sent if m["type"] == "http.response.start"]
        self.assertEqual(start_msgs[0]["status"], 200)

    # ---- 组合测试 ----

    def test_pipeline_from_config_to_sse(self):
        """全链路：UserLLMConfig → build_llm → stream_chat → SSE output"""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock, patch
        from langchain_core.messages import HumanMessage

        # 手动构建 LLM 消息
        raw = [
            {"role": "system", "content": "你是运维助手"},
            {"role": "user", "content": "组合测试"},
        ]

        # 1) build_pve_context 返回实际数据
        pve_ctx = build_pve_context(self.cluster.id, "节点")
        self.assertIn("fullnode", pve_ctx)

        # 2) build_langchain_messages 正确组装
        msgs = build_langchain_messages(raw, pve_context=pve_ctx)
        from langchain_core.messages import SystemMessage
        self.assertIsInstance(msgs[0], SystemMessage)
        self.assertIn("fullnode", msgs[0].content)
        self.assertIn("运维助手", msgs[0].content)

        # 3) build_llm 实例化
        llm = build_llm(self.config)
        self.assertIsNotNone(llm)
        self.assertEqual(llm.model_name, "deepseek-v4-pro")

        # 4) stream_chat mock 验证
        mock_llm = AsyncMock()
        async def mock_astream(_):
            for t in ["组合", "测试", "结果"]:
                chunk = MagicMock()
                chunk.content = t
                yield chunk
        mock_llm.astream = mock_astream

        async def run():
            tokens = []
            async for t in stream_chat(mock_llm, msgs):
                tokens.append(t)
            return tokens

        tokens = asyncio.run(run())
        self.assertEqual(tokens, ["组合", "测试", "结果"])

    def test_pipeline_without_cluster(self):
        """全链路无 cluster_id：不注入 PVE context，LLM 正常流式"""
        from unittest.mock import AsyncMock, MagicMock, patch

        raw = [
            {"role": "user", "content": "你好"},
        ]
        # 没有 cluster_id → pve_context 为空
        msgs = build_langchain_messages(raw, pve_context="")
        self.assertEqual(len(msgs), 1)

        mock_llm = AsyncMock()
        async def mock_astream(_):
            chunk = MagicMock()
            chunk.content = "你好，有什么可以帮助？"
            yield chunk
        mock_llm.astream = mock_astream

        async def run():
            tokens = []
            async for t in stream_chat(mock_llm, msgs):
                tokens.append(t)
            return tokens

        tokens = asyncio.run(run())
        self.assertEqual(tokens, ["你好，有什么可以帮助？"])

    def test_pipeline_multiple_config_providers(self):
        """多个不同 provider 配置都能正确走通"""
        providers = ['deepseek', 'openai', 'kimi', 'glm', 'custom']
        for provider in providers:
            cfg = UserLLMConfig(
                user=self.user, name=f"test-{provider}",
                api_key="sk-test",
                provider=provider,
                model=f"model-{provider}",
                base_url=f"https://api.{provider}.example.com",
            )
            llm = build_llm(cfg)
            self.assertIsNotNone(llm)
            expected_keyword = provider if provider != 'custom' else 'custom'
            self.assertIn(expected_keyword, llm.openai_api_base or "")
            self.assertEqual(llm.model_name, f"model-{provider}")
