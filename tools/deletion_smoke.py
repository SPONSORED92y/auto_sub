"""Exercise sentence deletion, undo, export persistence and punctuation clarity."""
import json
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
        rows = frame.locator("tbody tr")
        expect(rows.first).to_be_visible()
        initial = rows.count()
        snapshot = """() => Array.from(document.querySelectorAll('tbody tr')).map(row=>({
          start:row.querySelector('[data-field=start]').value,
          end:row.querySelector('[data-field=end]').value,text:row.querySelector('textarea').value}))"""
        original = frame.locator("body").evaluate(snapshot)
        delete = frame.get_by_role("button",name="刪除句子",exact=True)
        expect(delete).to_be_disabled()
        core = frame.locator("body").evaluate("""() => {
          const rows=[{start:0,end:1,text:'甲'},{start:2,end:3,text:'乙'}];
          return {empty:EditorCore.deleteCue(rows,0), invalid:EditorCore.deleteCue(rows,9), source:rows};
        }""")
        assert len(core["empty"])==1 and len(core["source"])==2 and core["invalid"] is None
        audio=frame.locator("audio")
        audio.evaluate("el=>{el.pause();el.currentTime=.7;}")
        frame.get_by_role("spinbutton",name="第 2 句開始時間",exact=True).click()
        expect(frame.locator("#selected-cue")).to_have_text("已選取第 2 句")
        delete.click()
        expect(rows).to_have_count(initial-1)
        assert frame.locator("body").evaluate(snapshot)==original[:1]+original[2:]
        assert abs(audio.evaluate("el=>el.currentTime")-.7)<.05 and audio.evaluate("el=>el.paused")
        expect(frame.locator("#message")).to_contain_text("已同步",timeout=15000)
        with page.expect_download() as downloaded:
            page.get_by_role("button",name="儲存專案 JSON",exact=True).click()
        project=json.loads(Path(downloaded.value.path()).read_text(encoding="utf-8"))
        assert len(project["cues"])==initial-1
        assert project["cues"][1]["text"]==original[2]["text"]
        frame.get_by_role("button",name="復原",exact=True).click()
        expect(rows).to_have_count(initial)
        assert frame.locator("body").evaluate(snapshot)==original
        # One click must restore each deletion, including the very last cue.
        for remaining in range(initial-1,-1,-1):
            rows.first.locator("td").first.click()
            delete.click()
            expect(rows).to_have_count(remaining)
        expect(delete).to_be_disabled()
        expect(page.get_by_role("button",name="下載 SRT",exact=True)).to_be_disabled(timeout=15000)
        frame.get_by_role("button",name="復原",exact=True).click()
        expect(rows).to_have_count(1)
        assert frame.locator("body").evaluate(snapshot)[0]==original[-1]
        # The output mode must be visible, and removal preview auto-opens.
        page.get_by_test_id("stPopover").get_by_role("button").first.click()
        page.get_by_role("combobox",name="輸出標點方式",exact=True).click()
        page.get_by_role("option",name="移除標點",exact=True).click()
        page.get_by_role("heading",name="Auto Sub 本機字幕",exact=True).click()
        expect(page.get_by_text("目前 SRT 輸出：移除標點",exact=False)).to_be_visible()
        expect(page.locator("pre").first).to_be_visible()
        assert not errors, errors
        print("Passed: selected/time-field deletion, unchanged remaining times/audio, saved deletion, one-step undo, empty editor recovery, visible output mode")
        browser.close()


if __name__=="__main__":
    main()
