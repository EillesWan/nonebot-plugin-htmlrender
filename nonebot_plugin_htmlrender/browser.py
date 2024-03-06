#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Author         : yanyongyu
@Date           : 2021-03-12 13:42:43
@LastEditors    : yanyongyu
@LastEditTime   : 2021-11-01 14:05:41
@Description    : None
@GitHub         : https://github.com/yanyongyu
"""
__author__ = "yanyongyu"

from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from nonebot import get_plugin_config
from nonebot.log import logger
from playwright.async_api import Browser, Error, Page, Playwright, async_playwright

from .config import Config
import asyncio

config = get_plugin_config(Config)

_browser: Optional[Browser] = None
_playwright: Optional[Playwright] = None


async def init(**kwargs) -> Browser:
    global _browser
    global _playwright
    _playwright = await async_playwright().start()
    try:
        _browser = await launch_browser(**kwargs)
    except Error:
        await install_browser()
        _browser = await launch_browser(**kwargs)
    return _browser


async def launch_browser(**kwargs) -> Browser:
    assert _playwright is not None, "Playwright 没有安装"

    if config.htmlrender_browser_channel:
        kwargs["channel"] = config.htmlrender_browser_channel

    if config.htmlrender_proxy_host:
        kwargs["proxy"] = {
            "server": config.htmlrender_proxy_host,
        }
    if config.htmlrender_browser == "firefox":
        logger.info("使用 firefox 启动")
        return await _playwright.firefox.launch(**kwargs)

    # 默认使用 chromium
    logger.info("使用 chromium 启动")
    return await _playwright.chromium.launch(**kwargs)


async def get_browser(**kwargs) -> Browser:
    return _browser if _browser and _browser.is_connected() else await init(**kwargs)


@asynccontextmanager
async def get_new_page(device_scale_factor: float = 2, **kwargs) -> AsyncIterator[Page]:
    browser = await get_browser()
    page = await browser.new_page(device_scale_factor=device_scale_factor, **kwargs)
    try:
        yield page
    finally:
        await page.close()


async def shutdown_browser():
    global _browser
    global _playwright
    if _browser:
        if _browser.is_connected():
            await _browser.close()
        _browser = None
    if _playwright:
        await asyncio.wait_for(_playwright.stop(), timeout=3)
        _playwright = None


async def install_browser():
    import os
    import sys

    from playwright.__main__ import main

    if host := config.htmlrender_download_host:
        logger.info("使用配置源进行下载")
        os.environ["PLAYWRIGHT_DOWNLOAD_HOST"] = host
    else:
        logger.info("使用镜像源进行下载")
        os.environ["PLAYWRIGHT_DOWNLOAD_HOST"] = (
            "https://npmmirror.com/mirrors/playwright/"
        )
    success = False

    if config.htmlrender_browser == "firefox":
        logger.info("正在安装 firefox")
        sys.argv = ["", "install", "firefox"]
    else:
        # 默认使用 chromium
        logger.info("正在安装 chromium")
        sys.argv = ["", "install", "chromium"]
    try:
        logger.info("正在安装依赖")
        os.system("playwright install-deps")  # noqa: ASYNC102, S605, S607
        main()
    except SystemExit as e:
        if e.code == 0:
            success = True
    if not success:
        logger.error("浏览器更新失败, 请检查网络连通性")
