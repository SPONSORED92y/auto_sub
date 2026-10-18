"""Check live output-mode changes without re-transcribing or changing drafts."""
import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width":1450,"height":1100})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto("http://127.0.0.1:8501", wait_until="networkidle")
        page.locator('input[type="file"]').first.set_input_files(ROOT/"outputs/smoke-bilingual.wav")
        page.get_by_text("開啟已儲存專案", exact=True).click()
        page.locator('input[type="file"]').nth(1).set_input_files(ROOT/"outputs/smoke-bilingual.turbo.cuda.autosub.json")
        page.get_by_role("button", name="載入專案", exact=True).click()
        expect(page.get_by_role("heading", name="編輯字幕", exact=True)).to_be_visible(timeout=30000)
        frame = page.locator("iframe").first.content_frame
        text = "你好，世界。3.3V Wi-Fi don't"
        frame.get_by_role("textbox", name="第 1 句字幕", exact=True).fill(text)
        frame.locator("#clock").click()
        page.get_by_text("預覽字幕", exact=True).click()
        expect(page.locator("pre").first).to_contain_text(text, timeout=15000)
        times = re.findall(r"\d+:\d+:\d+,\d+ --> \d+:\d+:\d+,\d+", page.locator("pre").first.inner_text())
        cases = [("移除標點","remove","你好世界3.3V Wi-Fi don't"),
                 ("標點改成空格","spaces","你好 世界 3.3V Wi-Fi don't"),
                 ("保留標點","keep",text)]
        for label, mode, expected in cases:
            page.get_by_test_id("stPopover").get_by_role("button").first.click()
            page.get_by_role("combobox", name="輸出標點方式", exact=True).click()
            page.get_by_role("option", name=label, exact=True).click()
            page.get_by_role("heading", name="Auto Sub 本機字幕", exact=True).click()
            expect(page.locator("pre").first).to_contain_text(expected, timeout=15000)
            preview = page.locator("pre").first.inner_text()
            assert re.findall(r"\d+:\d+:\d+,\d+ --> \d+:\d+:\d+,\d+", preview) == times
            assert frame.get_by_role("textbox", name="第 1 句字幕", exact=True).input_value() == text
            with page.expect_download() as downloaded:
                page.get_by_role("button", name="下載 SRT", exact=True).click()
            assert Path(downloaded.value.path()).read_text(encoding="utf-8").strip() == preview.strip()
            with page.expect_download() as downloaded:
                page.get_by_role("button", name="儲存專案 JSON", exact=True).click()
            project = json.loads(Path(downloaded.value.path()).read_text(encoding="utf-8"))
            assert project["metadata"]["export_settings"]["punctuation"] == mode
            assert project["cues"][0]["text"] == text
        assert not errors, errors
        print("Passed: keep/remove/spaces, live preview/download agreement, unchanged draft/times, saved export preference")
        browser.close()


if __name__ == "__main__":
    main()
