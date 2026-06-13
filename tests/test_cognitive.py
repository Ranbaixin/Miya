"""认知记忆系统测试

测试 JobQueue, ProfileStorage, VectorStore, CognitiveService
"""

import time

import pytest

# ============================================================================
# JobQueue 测试
# ============================================================================


@pytest.mark.asyncio
async def test_jobqueue_enqueue_dequeue(job_queue):
    """测试任务入队/出队"""
    job_id = await job_queue.enqueue(
        {
            "job_id": "test-001",
            "text": "然鑫喜欢咖啡",
            "group_id": 123,
            "user_id": 456,
        }
    )
    assert job_id == "test-001"

    assert await job_queue.pending_count() == 1

    job = await job_queue.dequeue()
    assert job is not None
    assert job["text"] == "然鑫喜欢咖啡"
    assert job["group_id"] == 123

    assert await job_queue.pending_count() == 0


@pytest.mark.asyncio
async def test_jobqueue_retry_flow(job_queue):
    """测试重试流程"""
    await job_queue.enqueue(
        {
            "job_id": "retry-001",
            "text": "测试重试",
            "_retry_count": 0,
        }
    )

    job = await job_queue.dequeue()
    assert job is not None

    # requeue (重试)
    await job_queue.requeue(job)
    assert await job_queue.pending_count() == 1

    # 再次出队（应有递增的重试计数）
    job2 = await job_queue.dequeue()
    assert job2 is not None
    assert job2["_retry_count"] == 1


@pytest.mark.asyncio
async def test_jobqueue_fail(job_queue):
    """测试失败处理"""
    await job_queue.enqueue(
        {
            "job_id": "fail-001",
            "text": "会失败的任务",
        }
    )
    job = await job_queue.dequeue()
    assert job is not None

    await job_queue.fail(job)
    # 确认 pending 和 processing 都为空
    assert await job_queue.pending_count() == 0
    assert await job_queue.processing_count() == 0


# ============================================================================
# ProfileStorage 测试
# ============================================================================


@pytest.mark.asyncio
async def test_profile_storage_write_read(profile_storage):
    """测试侧写写入和读取"""
    await profile_storage.write_profile(
        entity_type="user",
        entity_id=456,
        profile_data={"display_name": "然鑫", "tags": ["coffee", "coding"]},
        body="# 然鑫的用户侧写\n\n然鑫喜欢喝咖啡和编程。",
    )

    profile = await profile_storage.read_profile("user", 456)
    assert profile is not None
    assert profile["display_name"] == "然鑫"
    assert "coffee" in profile["tags"]
    assert "咖啡" in profile["_body"]


@pytest.mark.asyncio
async def test_profile_storage_delete(profile_storage):
    """测试侧写删除"""
    await profile_storage.write_profile(
        entity_type="group",
        entity_id=999,
        profile_data={"name": "测试群"},
        body="这是一个测试群。",
    )

    profile = await profile_storage.read_profile("group", 999)
    assert profile is not None

    deleted = await profile_storage.delete_profile("group", 999)
    assert deleted is True

    profile = await profile_storage.read_profile("group", 999)
    assert profile is None


# ============================================================================
# CognitiveService 测试
# ============================================================================


@pytest.mark.asyncio
async def test_cognitive_service_record_observation(cognitive_service):
    """测试记录观察"""
    job_id = await cognitive_service.record_observation(
        text="然鑫今天心情很好",
        group_id=123,
        user_id=456,
        source_type="chat",
    )
    assert job_id
    assert await cognitive_service.job_queue.pending_count() == 1


@pytest.mark.asyncio
async def test_cognitive_service_add_event(cognitive_service):
    """测试直接添加向量事件"""
    await cognitive_service.add_event_directly(
        event_id="evt-001",
        text="然鑫向弥娅道了早安",
        metadata={
            "group_id": "123",
            "user_id": "456",
            "timestamp": time.time(),
        },
    )

    events = await cognitive_service.search_events(query="早安", top_k=3)
    assert len(events) > 0
    assert any("早安" in (e.get("text") or "") for e in events)


@pytest.mark.asyncio
async def test_cognitive_service_build_context(cognitive_service):
    """测试构建上下文"""
    # 添加一个事件
    await cognitive_service.add_event_directly(
        event_id="ctx-001",
        text="然鑫在群里分享了关于 docker 的文章",
        metadata={
            "group_id": "123",
            "user_id": "456",
            "timestamp": time.time(),
        },
    )

    context = await cognitive_service.build_context(
        query="docker",
        group_id=123,
        user_id=456,
    )
    assert "<cognitive_memory>" in context
    assert "docker" in context


@pytest.mark.asyncio
async def test_cognitive_service_update_profile(cognitive_service):
    """测试更新侧写"""
    await cognitive_service.update_profile(
        entity_type="user",
        entity_id=456,
        profile_data={"display_name": "然鑫", "emoji": "☕"},
        body="然鑫喜欢喝咖啡和编程。",
    )

    profiles = await cognitive_service.search_profiles(query="咖啡", top_k=3)
    assert len(profiles) > 0


# ============================================================================
# 边界条件测试
# ============================================================================


@pytest.mark.asyncio
async def test_cognitive_service_empty_search(cognitive_service):
    """测试空搜索"""
    events = await cognitive_service.search_events(
        query="不存在的查询xyz123",
        top_k=3,
    )
    # 空集合应该返回空列表
    assert isinstance(events, list)


@pytest.mark.asyncio
async def test_profile_storage_nonexistent(profile_storage):
    """测试读取不存在的侧写"""
    profile = await profile_storage.read_profile("user", 99999)
    assert profile is None
