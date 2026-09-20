"""Optional Playwright check for a generated local browser; no model calls."""
from __future__ import annotations
import contextlib
import functools
import json
import threading
import sys
from pathlib import Path
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer


def check(site:Path,out:Path,chromium:str|None=None,*,memory:bool=False):
    from playwright.sync_api import sync_playwright,expect
    site=Path(site).resolve();out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(site)))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    url=site.as_uri()+'/'
    errors=[];requests=[];results=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,executable_path=chromium,args=['--no-sandbox'])
            page=browser.new_page(viewport={'width':1440,'height':1024},device_scale_factor=1)
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
            page.on('request',lambda r:requests.append(r.url))
            if memory:
                import re
                text=(site/'index.html').read_text()
                # This mode tests only DOM/CSS/JS behavior. It does not navigate,
                # access blocked URLs, or certify CSP/static-file hosting.
                text=re.sub(r'<meta http-equiv="Content-Security-Policy"[^>]*>','',text)
                text=text.replace('<link rel="stylesheet" href="app.css">','')
                text=text.replace('<script src="app.js"></script>','')
                page.set_content(text,wait_until='load')
                page.add_style_tag(content=(site/'app.css').read_text())
                page.evaluate((site/'app.js').read_text())
            else:
                page.goto(url+'index.html',wait_until='load')
            page.wait_for_timeout(300)
            assert page.locator('#page-title').inner_text()=='Research overview'
            assert page.locator('.stat').count()==4
            assert page.locator('#filters').is_hidden()
            page.screenshot(path=str(out/'desktop-overview.png'),full_page=True)
            page.locator('[data-route="runs"]').click();expect(page.locator('#page-title')).to_have_text('Experiments')
            expect(page.locator('#filters')).to_be_visible()
            assert page.locator('tbody tr').count()>=2
            title=page.locator('tbody .record-link').first.inner_text()
            page.locator('#search').fill('no-record-should-have-this-title')
            expect(page.locator('.empty')).to_be_visible()
            page.locator('#search').fill('')
            page.locator('tbody .record-link').first.click()
            expect(page.locator('#detail')).to_be_visible()
            assert page.locator('#detail-title').inner_text()==title
            page.keyboard.press('Escape');expect(page.locator('#detail')).not_to_be_visible()
            results+=['overview','search','record_dialog','escape_close']
            page.locator('[data-route="claims"]').click();expect(page.locator('#page-title')).to_have_text('Research claims');expect(page.locator('tbody tr')).to_have_count(1)
            page.locator('tbody .record-link').first.click();assert 'Recorded attempts' in page.locator('#detail-body').inner_text()
            page.locator('#close-detail').click()
            page.locator('[data-route="attempts"]').click();expect(page.locator('#page-title')).to_have_text('Execution & reproduction attempts');expect(page.locator('tbody tr')).to_have_count(2)
            page.locator('[data-route="compare"]').click();expect(page.locator('#page-title')).to_have_text('Compare experiments')
            assert page.locator('#compare-left').count()==1
            page.locator('#compare-right').select_option(page.locator('#compare-left').input_value())
            assert 'same run selected' in page.locator('#content').inner_text()
            page.screenshot(path=str(out/'desktop-comparison.png'),full_page=True)
            results+=['legacy_claims','attempts','comparison_guard']
            with page.expect_download() as event:page.locator('#download').click()
            downloaded=event.value;downloaded.save_as(str(out/'downloaded-catalog.json'))
            assert json.loads((out/'downloaded-catalog.json').read_text())['format']=='cvrs-static-browser/1'
            page.set_viewport_size({'width':390,'height':844})
            page.locator('[data-route="overview"]').click();expect(page.locator('#page-title')).to_have_text('Research overview')
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1')
            page.screenshot(path=str(out/'mobile-overview.png'),full_page=True)
            results+=['catalogue_download','mobile_no_page_overflow']
            browser.close()
    finally:server.shutdown();server.server_close();thread.join(timeout=3)
    remote=[x for x in requests if not x.startswith(url) and not x.startswith('blob:')]
    result={'status':'PASSED' if not errors and not remote else 'FAILED','checks':results,'console_errors':errors,
        'unexpected_remote_requests':remote,'browser':'Chromium Playwright','transport':'in-memory render' if memory else 'file:// offline','source':str(site),
        'limits':'Interface behavior only. In-memory mode does not validate CSP, navigation/hosting, scientific claims or native-model compatibility.'}
    (out/'summary.json').write_text(json.dumps(result,indent=2))
    if result['status']!='PASSED':raise RuntimeError(json.dumps(result))
    return result


if __name__=='__main__':
    print(json.dumps(check(Path(sys.argv[1]),Path(sys.argv[2]),sys.argv[3] if len(sys.argv)>3 else None,memory='--memory' in sys.argv),indent=2))
