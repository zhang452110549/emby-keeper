import asyncio
import random
import re

from pyrogram.errors import MessageIdInvalid
from pyrogram.types import Message

from ._templ_a import TemplateACheckin


class MICUCheckin(TemplateACheckin):
    name = "MICU 股东会"
    bot_username = "micu_user_bot"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._math_solved = False

    async def on_button_answer(self, answer):
        if not self._math_solved:
            return
        await super().on_button_answer(answer)

    async def message_handler(self, client, message: Message):
        text = message.caption or message.text
        self.log.debug(
            f"[gray50]收到消息: text={repr(text[:80] if text else None)}, "
            f"has_markup={bool(message.reply_markup)}, edit_date={message.edit_date}[/]"
        )
        if text and message.reply_markup:
            norm = text.replace("×", "*").replace("÷", "/").replace("−", "-").replace("－", "-")
            if re.search(r"\d+\s*[-+*/]\s*\d+\s*[=＝]\s*[?？]", norm):
                await self.on_math_captcha(message, norm)
                return
        await super().message_handler(client, message)

    async def on_math_captcha(self, message: Message, norm_text: str):
        keys = [k.text for r in message.reply_markup.inline_keyboard for k in r]
        self.log.debug(f"[gray50]答题消息原文: {repr(norm_text[:120])}[/]")
        self.log.debug(f"[gray50]可选按钮: {keys}[/]")

        match = re.search(r"(\d+)\s*([-+*/])\s*(\d+)", norm_text)
        if not match:
            self.log.warning("签到失败: 未知的数学题格式.")
            return await self.fail()

        a, op, b = int(match.group(1)), match.group(2), int(match.group(3))
        if op == "/" and b == 0:
            self.log.warning("签到失败: 数学题除数为零.")
            return await self.fail()
        result = {"+": a + b, "-": a - b, "*": a * b, "/": a // b}[op]
        self.log.info(f"数学题: {a} {op} {b} = {result}, 选择按钮: {repr(str(result))}")

        for k in keys:
            if k.strip() == str(result):
                self.log.debug(f"[gray50]点击答案按钮: {repr(k)}[/]")
                await asyncio.sleep(random.uniform(2, 4))
                try:
                    answer = await message.click(k)
                except TimeoutError:
                    self.log.debug("点击答案按钮无响应, 正在重试.")
                    return await self.retry()
                except MessageIdInvalid:
                    self._math_solved = True
                else:
                    self._math_solved = True
                    await self.on_button_answer(answer)
                return

        self.log.warning(f"签到失败: 未找到答案按钮 {result} (可选: {keys}).")
        await self.fail()
