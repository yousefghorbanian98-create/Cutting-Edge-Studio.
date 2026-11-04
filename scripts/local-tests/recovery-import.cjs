// Real browser + backend R1 acceptance. External tools via NODE_PATH; no mocked HTTP.
const chromium = require('@sparticuz/chromium').default;
const { chromium: pw } = require('playwright');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const out = process.env.CE_E2E_OUTPUT || path.resolve(__dirname, '../../docs/evidence/recovery-r1');
fs.mkdirSync(out, {recursive:true});
const digest = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
(async () => {
  const browser = await pw.launch({executablePath: await chromium.executablePath(), args: chromium.args, headless:true});
  try {
    const page = await browser.newPage({viewport:{width:1920,height:1080}});
    const checks=[], uploads=[], errors=[], requests=[], responseTasks=[];
    const base = process.env.CE_E2E_UI || 'http://127.0.0.1:1420';
    const apiUrl = route => new URL(route, base).href;
    const check=(name,ok,detail='')=>{ checks.push({name,passed:!!ok,detail}); console.log(ok?'PASS':'FAIL', name, detail); };
    page.on('pageerror',e=>errors.push(e.message));
    page.on('request',r=>{if(r.url().includes('/api/')) requests.push({method:r.method(),url:r.url()});});
    page.on('response',r=>{
      if(r.url().endsWith('/uploads') && r.status()===201) responseTasks.push(r.json().then(body=>uploads.push(body)));
    });
    await page.goto(base);
    await page.getByRole('button',{name:'زبان',exact:true}).click();
    const sourceInput = page.getByLabel('Import clips',{exact:true});
    const files=Array.from({length:10},(_,i)=>`/tmp/ce-media/clips/clip${i+1}.mp4`);
    await sourceInput.setInputFiles(files);
    await page.waitForFunction(()=>document.querySelectorAll('li[data-testid^="clip-"]').length===10,{},{timeout:60000});
    await Promise.all(responseTasks);
    check('Ten real uploads complete',uploads.length===10);
    check('Only one backend project created',requests.filter(r=>r.method==='POST' && r.url.endsWith('/projects')).length===1);
    const project=uploads[0].project_id;
    const listing=await (await page.request.get(apiUrl(`/api/v1/projects/${project}/assets`))).json();
    check('All ten assets persisted in backend',listing.length===10 && listing.every(a=>a.duration>0 && a.width===1080 && a.height===1920));
    const first=uploads[0];
    check('Uploaded bytes match original SHA-256',digest(fs.readFileSync(first.path))===digest(fs.readFileSync(files[0])));
    check('Backend storage path replaces browser filename',first.path!==path.basename(files[0]) && first.path.includes('/imports/'));
    const partial=await page.request.get(apiUrl(`/api/v1/assets/${first.id}/content`),{headers:{Range:'bytes=0-127'}});
    check('Content endpoint supports HTTP Range',partial.status()===206 && (await partial.body()).length===128);
    await page.getByRole('button',{name:'clip1.mp4',exact:true}).click();
    let loaded=true;
    try { await page.waitForFunction(()=>document.querySelector('video')?.readyState>=2,{},{timeout:15000}); }
    catch(error) { console.error('playback.wait.failed',error.message); loaded=false; }
    const state=await page.locator('video').evaluate(v=>({readyState:v.readyState,duration:v.duration,error:v.error?.message||null}));
    check('Browser decodes imported source',loaded && state.duration>0,JSON.stringify(state));
    if(loaded) {
      await page.locator('video').evaluate(async v=>{v.muted=true;await v.play();});
      await page.waitForTimeout(450);
      const advanced=await page.locator('video').evaluate(v=>v.currentTime);
      check('Native source playback advances',advanced>0,`${advanced}s`);
      await page.locator('video').evaluate(v=>{v.pause();v.currentTime=1;});
    }
    await page.getByRole('button',{name:'Add to timeline clip1.mp4',exact:true}).click();
    await page.locator('.timeline-editor-action').first().waitFor();
    check('Imported source appears on timeline',await page.locator('.timeline-editor-action').count()===1);
    await page.screenshot({path:path.join(out,'01-real-import-and-playback.png')});
    await page.getByRole('button',{name:'Remove clip1.mp4',exact:true}).click();
    await page.getByRole('alert').filter({hasText:'Remove the clip from the timeline'}).waitFor();
    check('Media in use cannot be deleted out from under timeline',await page.locator('li[data-testid^="clip-"]').count()===10);
    const countBefore=uploads.length;
    await sourceInput.setInputFiles([files[0]]);
    await page.getByRole('alert').waitFor();
    check('Duplicate import rejected before upload',uploads.length===countBefore);
    await page.getByLabel('Import reference video',{exact:true}).setInputFiles('/tmp/ce-media/ref/reference.mp4');
    await page.waitForFunction(()=>document.querySelectorAll('li[data-testid^="clip-"]').length===11,{},{timeout:30000});
    await Promise.all(responseTasks);
    check('Reference imported with explicit role',uploads.length===11 && uploads[10].role==='reference');
    await page.getByRole('button',{name:'Reference intake',exact:true}).click();
    for(let i=0;i<4;i++){await page.getByTestId('wizard-next').click();await page.waitForTimeout(220);}
    check('Unavailable analysis is blocked, not fake success',await page.getByTestId('wizard-next').isDisabled());
    check('Unavailable edit render is blocked',await page.getByRole('button',{name:'Build preview',exact:true}).isDisabled());
    await page.screenshot({path:path.join(out,'02-explicit-reference-and-analysis-gate.png')});
    await sourceInput.setInputFiles({name:'broken.mp4',mimeType:'video/mp4',buffer:Buffer.from('not a media container')});
    await page.getByRole('alert').filter({hasText:'ffprobe unavailable'}).waitFor({timeout:30000});
    check('Invalid media has visible backend error',await page.locator('li[data-testid^="clip-"]').count()===11);
    const finalList=await (await page.request.get(apiUrl(`/api/v1/projects/${project}/assets`))).json();
    check('Failed import creates no phantom DB asset',finalList.length===11);
    await page.getByRole('button',{name:'Remove reference.mp4',exact:true}).click();
    await page.waitForFunction(()=>document.querySelectorAll('li[data-testid^="clip-"]').length===10);
    await page.getByRole('button',{name:'1. Reference intake',exact:true}).click();
    await page.waitForTimeout(220);
    check('Deleted reference cannot satisfy analysis gate',await page.getByTestId('wizard-next').isDisabled());
    check('No browser page exceptions' ,errors.length===0,JSON.stringify(errors));
    const result={checks,project,uploads,errors,requests,limits:['Source playback only; not timeline-composited playback.','No real model analysis, compliant export, or Windows acceptance claimed.']};
    fs.writeFileSync(path.join(out,'browser-results.json'),JSON.stringify(result,null,2));
    process.exitCode=checks.every(c=>c.passed)?0:1;
  } finally { await browser.close(); }
})().catch(error=>{console.error('recovery.import.test.failed',error);process.exitCode=1;});
