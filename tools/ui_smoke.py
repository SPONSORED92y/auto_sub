"""Run against the local Streamlit server using installed Microsoft Edge.

Requires: pip install -e '.[ui-test]'. Uses generated smoke-bilingual.wav;
tests edit a browser session only, without changing source audio.
"""
from pathlib import Path
import base64
import json
import re

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True,
                                   args=["--autoplay-policy=no-user-gesture-required"])
        page = browser.new_page(viewport={"width": 1450, "height": 1100})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto("http://127.0.0.1:8501", wait_until="networkidle")
        page.locator('input[type="file"]').first.set_input_files(ROOT / "outputs/smoke-bilingual.wav")
        page.get_by_text("僅使用已下載模型（離線）", exact=True).click()
        start_box = page.get_by_role("button", name="開始辨識", exact=True).bounding_box()
        settings_box = page.get_by_test_id("stPopover").get_by_role("button").first.bounding_box()
        assert 0 <= settings_box["x"] - (start_box["x"]+start_box["width"]) <= 25
        page.get_by_test_id("stPopover").get_by_role("button").first.click()
        expect(page.get_by_label("提供專有名詞提示", exact=True)).to_be_visible()
        page.get_by_label("提供專有名詞提示", exact=True).fill("ESP32, Arduino")
        page.get_by_label("提供專有名詞提示", exact=True).press("Tab")
        # Widget help icons must have actual hover explanations, not just labels.
        widget = page.get_by_test_id("stTextInput").filter(has=page.get_by_text("提供專有名詞提示", exact=True))
        widget.locator('[data-testid="stTooltipIcon"]').hover()
        expect(page.get_by_role("tooltip")).to_contain_text("不是強制取代字典")
        page.screenshot(path=str(ROOT / "outputs/settings-ui.png"), full_page=True)
        page.get_by_role("heading", name="Auto Sub 本機字幕", exact=True).click()
        page.get_by_role("button", name="開始辨識", exact=True).click()
        expect(page.get_by_role("heading", name="編輯字幕", exact=True)).to_be_visible(timeout=60000)
        iframe = page.locator("iframe").first
        expect(iframe).to_be_visible(timeout=30000)
        frame = iframe.content_frame
        expect(frame.locator("tbody tr").first).to_be_visible(timeout=30000)
        count = frame.locator("tbody tr").count()
        if count < 4:
            print("Initial rows:", frame.locator("tbody").inner_text())
            print("Page:", page.locator("body").inner_text())
            page.screenshot(path=str(ROOT / "outputs/editor-debug.png"), full_page=True)
        assert count >= 4
        assert page.get_by_text("跳至字幕", exact=True).count() == 0
        assert page.get_by_role("button", name="從這句播放").count() == 0

        # Row clicks seek without toggling pause/play; time buttons do not seek.
        audio = frame.locator("audio")
        audio.evaluate("el => {el.pause();el.currentTime=0;}")
        target = float(frame.get_by_role("spinbutton", name="第 3 句開始時間", exact=True).input_value())
        frame.get_by_role("textbox", name="第 3 句字幕", exact=True).click()
        assert audio.evaluate("el => el.paused")
        assert abs(audio.evaluate("el => el.currentTime")-target)<0.05
        audio.evaluate("el => el.play()")
        target = float(frame.get_by_role("spinbutton", name="第 2 句開始時間", exact=True).input_value())
        frame.get_by_role("textbox", name="第 2 句字幕", exact=True).click()
        assert not audio.evaluate("el => el.paused")
        assert target <= audio.evaluate("el => el.currentTime") < target+0.7
        audio.evaluate("el => el.pause()")

        # Pure edit operations, including merge restrictions at both edges.
        core = frame.locator("body").evaluate("""() => {
          const c=[{start:0,end:2,text:'甲乙'},{start:3,end:4,text:'Hello'}], e=window.EditorCore;
          return {split:e.splitCue(c,0,1), noMiddle:e.mergeCue(c,0,1),
            noFirst:e.mergeCue(c,0,0), noLast:e.mergeCue(c,1,5),
            mergeStart:e.mergeCue(c,1,0), mergeEnd:e.mergeCue(c,0,2),
            active:e.activeIndex(c,3.5),gap:e.activeIndex(c,2.5)};
        }""")
        assert core["split"][0]["end"] is None and core["split"][1]["start"] is None
        assert core["noMiddle"] is None and core["noFirst"] is None and core["noLast"] is None
        assert len(core["mergeStart"]["cues"]) == len(core["mergeEnd"]["cues"]) == 1
        assert core["active"] == 1 and core["gap"] == -1

        # Cursor operations in the real rendered editor.
        text = frame.get_by_role("textbox", name="第 1 句字幕", exact=True)
        text.evaluate("el => {el.focus();el.setSelectionRange(2,2);el.dispatchEvent(new Event('select'));}")
        expect(frame.get_by_role("button", name="向前合併", exact=True)).to_be_disabled()
        expect(frame.get_by_role("button", name="向後合併", exact=True)).to_be_disabled()
        frame.get_by_role("button", name="拆句", exact=True).click()
        expect(frame.locator("tbody tr")).to_have_count(count+1)
        expect(frame.get_by_role("spinbutton", name="第 1 句結束時間", exact=True)).to_have_value("")
        expect(frame.get_by_role("spinbutton", name="第 2 句開始時間", exact=True)).to_have_value("")
        expect(page.get_by_role("button", name="下載 SRT", exact=True)).to_be_disabled(timeout=15000)
        expect(page.get_by_role("button", name="儲存專案 JSON", exact=True)).to_be_enabled()
        frame.get_by_role("button", name="自動辨識斷句時間", exact=True).click()
        expect(frame.get_by_role("spinbutton", name="第 1 句結束時間", exact=True)).not_to_have_value("", timeout=60000)
        expect(frame.get_by_role("spinbutton", name="第 2 句開始時間", exact=True)).not_to_have_value("")
        expect(page.get_by_role("button", name="下載 SRT", exact=True)).to_be_enabled(timeout=15000)

        # Increment controls update both the cell and backend export state.
        start = frame.get_by_role("spinbutton", name="第 2 句開始時間", exact=True)
        before = float(start.input_value())
        frame.get_by_role("button", name="第 2 句開始 +0.1 秒", exact=True).click()
        expect(start).to_have_value(f"{before+0.1:.3f}")
        frame.get_by_role("button", name="第 2 句開始 -0.1 秒", exact=True).click()
        expect(start).to_have_value(f"{before:.3f}")

        # Real audio playback highlights the matching row and survives edits.
        time = float(start.input_value()) + 0.05
        frame.locator("audio").evaluate("(el,t) => {el.currentTime=t;return el.play();}", time)
        expect(frame.locator("tbody tr").nth(1)).to_have_class(re.compile(r"(?:^|\s)active(?:\s|$)"), timeout=5000)
        frame.get_by_role("button", name="第 2 句開始 +0.1 秒", exact=True).click()
        frame.locator("audio").evaluate("el => el.pause()")
        assert frame.locator("audio").evaluate("el => el.currentTime") >= time
        frame.get_by_role("button", name="第 2 句開始 -0.1 秒", exact=True).click()

        # Merge is enabled only at text boundaries; it removes the internal times.
        text = frame.get_by_role("textbox", name="第 2 句字幕", exact=True)
        text.evaluate("el => {el.focus();el.setSelectionRange(0,0);el.dispatchEvent(new Event('select'));}")
        expect(frame.get_by_role("button", name="向前合併", exact=True)).to_be_enabled()
        expect(frame.get_by_role("button", name="向後合併", exact=True)).to_be_disabled()
        frame.get_by_role("button", name="向前合併", exact=True).click()
        expect(frame.locator("tbody tr")).to_have_count(count)
        expect(frame.locator("#message")).to_contain_text("已同步", timeout=15000)

        # Unspoken edits cannot be timed safely: leave blanks and ask for input.
        text = frame.get_by_role("textbox", name="第 1 句字幕", exact=True)
        text.evaluate("el => {el.focus();el.setSelectionRange(2,2);el.dispatchEvent(new Event('select'));}")
        frame.get_by_role("button", name="拆句", exact=True).click()
        text = frame.get_by_role("textbox", name="第 1 句字幕", exact=True)
        text.fill(text.input_value() + "人工補註")
        frame.get_by_role("button", name="自動辨識斷句時間", exact=True).click()
        expect(page.get_by_text("仍有 2 個起訖時間無法可靠辨識", exact=False)).to_be_visible(timeout=60000)
        expect(frame.get_by_role("spinbutton", name="第 1 句結束時間", exact=True)).to_have_value("")
        expect(page.get_by_role("button", name="下載 SRT", exact=True)).to_be_disabled()
        with page.expect_download() as download:
            page.get_by_role("button", name="儲存專案 JSON", exact=True).click()
        project = json.loads(Path(download.value.path()).read_text(encoding="utf-8"))
        assert project["schema_version"] == 2 and project["cues"][0]["end"] is None
        frame.get_by_role("spinbutton", name="第 1 句結束時間", exact=True).fill("1")
        frame.get_by_role("spinbutton", name="第 2 句開始時間", exact=True).fill("1")
        frame.locator("#clock").click()
        expect(page.get_by_role("button", name="下載 SRT", exact=True)).to_be_enabled(timeout=15000)
        ROOT.joinpath("outputs").mkdir(exist_ok=True)
        page.screenshot(path=str(ROOT / "outputs/editor-ui.png"), full_page=True)
        # Read exported settings as evidence that the popover affected inference.
        with page.expect_download() as download:
            page.get_by_role("button", name="儲存專案 JSON", exact=True).click()
        project = json.loads(Path(download.value.path()).read_text(encoding="utf-8"))
        assert project["metadata"]["settings"]["hotwords"] == "ESP32, Arduino"

        # A long fixture exercises following across a genuinely scrollable table.
        component_url = iframe.element_handle().content_frame().url
        fixture = browser.new_page(viewport={"width":1000,"height":1000})
        fixture.goto(component_url)
        fixture.evaluate("""args => window.dispatchEvent(new MessageEvent('message', {
          source:window, data:{type:'streamlit:render',args}
        }))""", {"revision":1,"duration":17.248,"digest":"scroll-fixture",
                  "audio_src":"data:audio/wav;base64,"+base64.b64encode((ROOT/"outputs/smoke-bilingual.wav").read_bytes()).decode(),
                  "cues":[{"start":i*.8,"end":(i+1)*.8,"text":f"字幕 {i+1}"} for i in range(20)]})
        expect(fixture.locator("tbody tr")).to_have_count(20)
        fixture.get_by_role("button", name="同步音訊", exact=True).click()
        fixture.locator("audio").evaluate("el => el.currentTime=12")
        fixture.wait_for_function("document.querySelector('.scroll').scrollTop>500")
        expect(fixture.get_by_role("button", name="同步音訊", exact=True)).to_have_attribute("aria-pressed","true")
        fixture.locator(".scroll").hover()
        fixture.mouse.wheel(0,-120)
        expect(fixture.get_by_role("button", name="同步音訊", exact=True)).to_have_attribute("aria-pressed","false")
        # Set a position and wait for its scroll event before seeking again.
        fixture.locator(".scroll").evaluate("el => el.scrollTop=500")
        fixture.locator("audio").evaluate("el => el.currentTime=0.1")
        assert fixture.locator(".scroll").evaluate("el => el.scrollTop") == 500
        fixture.get_by_role("button", name="同步音訊", exact=True).click()
        fixture.wait_for_function("document.querySelector('.scroll').scrollTop<10")
        # Both directions enforce their own cursor boundary.
        text = fixture.get_by_role("textbox", name="第 2 句字幕", exact=True)
        text.evaluate("el => {el.focus();el.setSelectionRange(el.value.length,el.value.length);el.dispatchEvent(new Event('select'));}")
        expect(fixture.get_by_role("button", name="向前合併", exact=True)).to_be_disabled()
        expect(fixture.get_by_role("button", name="向後合併", exact=True)).to_be_enabled()
        fixture.get_by_role("button", name="向後合併", exact=True).click()
        expect(fixture.locator("tbody tr")).to_have_count(19)
        fixture.close()
        assert not errors, errors
        print(json.dumps({"result":"passed", "initial_cues":count,
                          "checks":["model order", "cursor split/merge", "pending export guard",
                                    "automatic timing", "time steps", "playback highlight", "playback continuity",
                                    "uncertain timing fallback", "draft download", "manual timing",
                                    "settings tooltips and parameter persistence", "row seek retains playback",
                                    "automatic following and manual-scroll cancellation", "directional merge"]}))
        browser.close()


if __name__ == "__main__":
    main()
