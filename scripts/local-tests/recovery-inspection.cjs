// R2a genuine local decode acceptance. NO network mocks or fixture metadata responses.
// Phases: prepare; restart backend; reopen (SIGKILLs test backend); restart; interrupted.
// External Playwright/Chromium + media fixtures stay outside Git; see the evidence report.
const chromium=require('@sparticuz/chromium').default;
const {chromium:pw}=require('playwright');
const fs=require('fs');
const path=require('path');
const crypto=require('crypto');
const assert=require('assert/strict');
const phase=process.argv[2];
const base=process.env.CE_E2E_UI || 'http://127.0.0.1:1421';
const out=process.env.CE_E2E_OUTPUT || path.resolve(__dirname,'../../docs/evidence/recovery-r2a');
const session=process.env.CE_SESSION_FILE || '/tmp/ce-r2a-run.json';
const url=route=>new URL(route,base).href;
const digest=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
fs.mkdirSync(out,{recursive:true});
const result=phase==='prepare'?{checks:[],requests:[],errors:[],limits:['Local source-built LGPL shared FFmpeg is diagnostic-only, NOT the approved pinned Windows BtbN runtime.','Media decode is NOT beats/shots/pose/sports/StyleDNA/EDL or export.']}:JSON.parse(fs.readFileSync(session));
function check(name,passed,detail=''){
  result.checks.push({phase,name,passed:!!passed,detail});console.log(passed?'PASS':'FAIL',name,detail);
  assert.ok(passed,name);
}
async function saved(page){await page.waitForFunction(()=>document.querySelector('[data-testid="workspace-status"]')?.textContent==='Saved locally',{},{timeout:20000});}
async function choose(page){
  await page.getByRole('button',{name:'Refresh projects',exact:true}).click();
  await page.getByRole('combobox',{name:'Open project',exact:true}).click();
  await page.getByRole('option',{name:`R2a — بررسی واقعی رسانه · ${result.project.slice(0,6)}`,exact:true}).click();
  await saved(page);
}
async function openPanel(page){
  await page.getByRole('button',{name:'3. Clip analysis',exact:true}).click();
  await page.getByTestId('inspection-panel').waitFor();
}
async function latest(page){const response=await page.request.get(url(`/api/v1/projects/${result.project}/inspection/latest`));assert.equal(response.status(),200);return response.json();}
async function start(page){
  const posted=page.waitForResponse(r=>r.url().endsWith('/inspection/jobs') && r.request().method()==='POST' && r.status()===202);
  await page.getByRole('button',{name:'Inspect media (decode)',exact:true}).click();
  return (await posted).json();
}
async function terminal(page,state){
  const labels={done:'Media decode verified — model analysis not performed',cancelled:'Inspection cancelled',failed:'Media inspection failed',interrupted:'Inspection interrupted by backend restart'};
  await page.getByTestId('inspection-state').filter({hasText:labels[state]}).waitFor({timeout:120000});
  const read=await latest(page);assert.equal(read.state,state);return read;
}
async function measuredReport(page){
  const report=await terminal(page,'done');
  assert.equal(report.percent,100);assert.equal(report.stale,false);
  assert.equal(report.report.scope,'media-inspection-only');assert.equal(report.report.files.length,11);
  for(const measurement of report.report.files){
    const asset=result.assets.find(a=>a.id===measurement.asset_id);
    assert.ok(asset);assert.equal(measurement.sha256,digest(fs.readFileSync(asset.path)));
    assert.ok(measurement.decoded_frames>0);assert.ok(measurement.decoded_seconds>0);
    assert.ok(measurement.duration>0);assert.equal(measurement.video_codec,'h264');
  }
  return report;
}
(async()=>{
  assert.ok(['prepare','reopen','interrupted'].includes(phase));
  const browser=await pw.launch({executablePath:await chromium.executablePath(),args:chromium.args,headless:true});
  try{
    const page=await browser.newPage({viewport:{width:1920,height:1080}});
    page.on('pageerror',error=>result.errors.push({phase,message:error.message}));
    page.on('request',r=>{if(r.url().includes('/api/'))result.requests.push({phase,method:r.method(),url:r.url()});});
    if(phase==='prepare'){
      await page.goto(base);await page.getByRole('button',{name:'زبان',exact:true}).click();
      result.assets=[];const tasks=[];
      page.on('response',r=>{if(r.url().endsWith('/uploads') && r.status()===201)tasks.push(r.json().then(a=>result.assets.push(a)));});
      await page.getByLabel('Import clips',{exact:true}).setInputFiles(Array.from({length:10},(_,i)=>`/tmp/ce-media/clips/clip${i+1}.mp4`));
      await page.waitForFunction(()=>document.querySelectorAll('li[data-testid^="clip-"]').length===10,{},{timeout:60000});
      await page.getByLabel('Import reference video',{exact:true}).setInputFiles({name:'مرجع.mp4',mimeType:'video/mp4',buffer:fs.readFileSync('/tmp/ce-media/ref/reference.mp4')});
      await page.getByRole('button',{name:'مرجع.mp4',exact:true}).waitFor();await Promise.all(tasks);
      result.project=result.assets[0].project_id;result.route=`/api/v1/projects/${result.project}/inspection`;
      check('Eleven actual imported assets belong to one project',result.assets.length===11 && result.assets.every(a=>a.project_id===result.project));
      await page.getByLabel('Project name',{exact:true}).fill('R2a — بررسی واقعی رسانه');
      await page.getByRole('button',{name:'Reference intake',exact:true}).click();await openPanel(page);await saved(page);
      const caps=await(await page.request.get(url(result.route+'/capabilities'))).json();
      check('Local decode available but inference explicitly blocked',caps.inspection.available && caps.model_analysis.available===false && caps.model_analysis.unavailable.includes('StyleDNA'));
      const first=await start(page);result.firstJob=first.id;
      await page.getByTestId('inspection-state').filter({hasText:'Inspecting actual media'}).waitFor({timeout:10000});
      const observed=await latest(page);
      check('Real running job has observed intermediate progress and no premature report',observed.state==='running' && observed.percent>0 && observed.percent<100 && observed.report===null,JSON.stringify({percent:observed.percent,message:observed.message}));
      await page.screenshot({path:path.join(out,'01-real-decode-running.png')});
      result.completed=await measuredReport(page);
      check('All eleven files fully decode with observed frames/time and independently matching SHA256',true,JSON.stringify(result.completed.report.files.map(f=>({name:f.name,frames:f.decoded_frames,seconds:f.decoded_seconds}))));
      const kinds=await(await page.request.get(url(`/api/v1/projects/${result.project}/stylematch/artifacts`))).json();
      check('Inspection stores no synthetic DNA or EDL',kinds.every(a=>a.kind==='media-inspection'));
      await page.reload();await saved(page);
      await terminal(page,'done');
      check('Browser reload restores committed report without starting a second job',result.requests.filter(r=>r.method==='POST' && r.url.endsWith('/inspection/jobs')).length===1);
      await page.getByRole('button',{name:'5. EDL build',exact:true}).click();
      check('Final model analysis and preview render remain blocked',await page.getByTestId('wizard-next').isDisabled() && await page.getByRole('button',{name:'Build preview',exact:true}).isDisabled());
      await openPanel(page);await saved(page);
      const cancelled=await start(page);
      await page.getByRole('button',{name:'Cancel inspection',exact:true}).click();
      const cancelledResult=await terminal(page,'cancelled');
      check('Cancellation terminates a genuine job without a fabricated report',cancelledResult.id===cancelled.id && cancelledResult.report===null && cancelledResult.percent<100);
      const victim=result.assets.find(a=>a.role==='source');const original=fs.readFileSync(victim.path);
      try{
        fs.writeFileSync(victim.path,'deliberately corrupt test container');await start(page);
        const failed=await terminal(page,'failed');
        check('Real FFprobe failure is visible and never becomes success',failed.error?.includes('command failed') && failed.report===null && failed.percent<100);
        await page.screenshot({path:path.join(out,'02-real-decoder-error.png')});
      }finally{fs.writeFileSync(victim.path,original);}
      const stale=await(await page.request.get(url(result.route+`/jobs/${result.firstJob}`))).json();
      check('Changed file invalidates the earlier measured report',stale.stale===true && stale.state==='done');
      await start(page);result.completed=await measuredReport(page);
      check('Explicit retry succeeds only after actual decoding and persistence',result.completed.id!==result.firstJob);
      await page.screenshot({path:path.join(out,'03-measured-result-models-blocked.png')});
      await saved(page);await page.getByRole('button',{name:'New project',exact:true}).click();await saved(page);await openPanel(page);
      check('A new project cannot inherit another project report or start with missing inputs',await page.getByRole('button',{name:'Inspect media (decode)',exact:true}).isDisabled() && await page.getByTestId('inspection-state').count()===0);
      const other=await page.evaluate(()=>localStorage.getItem('cutting-edge.last-project'));
      const denied=await page.request.get(url(`/api/v1/projects/${other}/inspection/jobs/${result.completed.id}`));
      check('Cross-project inspection reads are rejected',denied.status()===404);
      await choose(page);await terminal(page,'done');await saved(page);
      check('Reopening the original project recovers its report, not the blank project',(await latest(page)).id===result.completed.id);
      result.backendBefore=process.env.CE_BACKEND_PID;assert.ok(result.backendBefore);
    }else{
      await page.goto(base);
      check('Fresh browser has no last-project shadow document',await page.evaluate(()=>localStorage.getItem('cutting-edge.last-project'))===null);
      await page.getByRole('button',{name:'زبان',exact:true}).click();await choose(page);
      if(phase==='reopen'){
        check('Backend genuinely restarted with the same SQLite data',result.backendBefore!==process.env.CE_BACKEND_PID,`${result.backendBefore} -> ${process.env.CE_BACKEND_PID}`);
        const restored=await measuredReport(page);assert.deepStrictEqual(restored,result.completed);
        check('Independent browser after backend restart recovers identical committed measurements',true);
        const victim=result.assets[0];fs.renameSync(victim.path,victim.path+'.test-backup');
        try{
          await page.getByRole('button',{name:'Refresh inspection',exact:true}).click();
          await page.getByRole('alert').filter({hasText:'Inputs changed or are unavailable'}).waitFor();
          check('Missing input produces a stale report warning instead of a new analysis claim',(await latest(page)).stale===true);
        }finally{fs.renameSync(victim.path+'.test-backup',victim.path);}
        await page.getByRole('button',{name:'Refresh inspection',exact:true}).click();await terminal(page,'done');
        result.crashJob=(await start(page)).id;
        await page.getByTestId('inspection-state').filter({hasText:'Inspecting actual media'}).waitFor();
        const current=await latest(page);
        check('An actual unfinished job is running before the deliberate crash',current.id===result.crashJob && current.state==='running' && current.report===null);
        const pid=Number(process.env.CE_BACKEND_PID);
        assert.ok(fs.readFileSync(`/proc/${pid}/cmdline`,'utf8').includes('python'));
        result.crashedPid=pid;fs.writeFileSync(session,JSON.stringify(result,null,2));
        process.kill(pid,'SIGKILL');
        check('Test backend was deliberately killed without graceful job completion',true,`SIGKILL ${pid}`);
      }else{
        const interrupted=await terminal(page,'interrupted');
        check('Restart marks an orphaned active job interrupted, not completed',interrupted.id===result.crashJob && interrupted.report===null && interrupted.percent<100 && interrupted.error.includes('restarted'));
        await page.screenshot({path:path.join(out,'04-crash-interrupted-no-fake-result.png')});
        await start(page);result.retriedAfterCrash=await measuredReport(page);
        check('A real retry after crash performs new decodes and stores a new measured report',result.retriedAfterCrash.id!==result.crashJob);
        await page.screenshot({path:path.join(out,'05-recovered-after-crash.png')});
      }
    }
    check('No browser page exceptions',result.errors.length===0,JSON.stringify(result.errors));
  }finally{
    fs.writeFileSync(session,JSON.stringify(result,null,2));
    fs.writeFileSync(path.join(out,'browser-results.json'),JSON.stringify(result,null,2));
    await browser.close();
  }
})().catch(error=>{console.error('inspection.acceptance.failed',error);process.exitCode=1;});
