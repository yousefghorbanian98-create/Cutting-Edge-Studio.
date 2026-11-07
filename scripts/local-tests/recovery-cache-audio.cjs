// R2b4 real local FFmpeg/librosa regression after owned scratch integration. No mocked API or measurement responses.
// Owned fixtures, external test libraries and test-only socket guard are NOT bundled.
const chromium=require('@sparticuz/chromium').default;
const {chromium:pw}=require('playwright');
const fs=require('fs');
const path=require('path');
const crypto=require('crypto');
const assert=require('assert/strict');
const phase=process.argv[2];
const base=process.env.CE_E2E_UI || 'http://127.0.0.1:1421';
const out=process.env.CE_E2E_OUTPUT || path.resolve(__dirname,'../../docs/evidence/recovery-r2b4/audio-regression');
const session='/tmp/ce-r2d-audio-run.json';
const result=phase==='prepare'?{checks:[],errors:[],external:[],requests:[],limits:[
  'Diagnostic Linux LGPL shared tools and external dynamic SoXR, NOT approved Windows shipping runtime.',
  'Audio estimates only; no shot/pose/sports/StyleDNA/EDL/export acceptance.',
  'Percentages are observed extraction/file stages, NOT library iterations or ETA.',
]}:JSON.parse(fs.readFileSync(session));
const url=route=>new URL(route,base).href;
const hash=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
function check(name,passed,detail=''){result.checks.push({phase,name,passed:!!passed,detail});console.log(passed?'PASS':'FAIL',name,detail);assert.ok(passed,name);}
async function saved(page){await page.waitForFunction(()=>document.querySelector('[data-testid="workspace-status"]')?.textContent==='Saved locally',{},{timeout:20000});}
async function panel(page){
  await page.getByRole('button',{name:'3. Clip analysis',exact:true}).click();
  await page.getByRole('button',{name:'Audio rhythm (experimental)',exact:true}).click();
  await page.getByRole('button',{name:'Measure audio rhythm',exact:true}).waitFor();
}
async function choose(page){
  await page.getByRole('button',{name:'Refresh projects',exact:true}).click();
  await page.getByRole('combobox',{name:'Open project',exact:true}).click();
  await page.getByRole('option',{name:`R2b4 — ضرب‌آهنگ و کش · ${result.project.slice(0,6)}`,exact:true}).click();
  await saved(page);await panel(page);
}
async function latest(page,job){const r=await page.request.get(url(result.route+(job?`/jobs/${job}`:'/latest')));assert.equal(r.status(),200);return r.json();}
async function start(page){
  const posted=page.waitForResponse(r=>r.url().endsWith('/rhythm/jobs') && r.request().method()==='POST' && r.status()===202);
  await page.getByRole('button',{name:'Measure audio rhythm',exact:true}).click();
  return (await posted).json();
}
async function terminal(page,state){
  const labels={done:'Audio report saved — model analysis not performed',cancelled:'Audio job cancelled',failed:'Audio measurement failed',interrupted:'Audio job interrupted by backend restart'};
  await page.getByTestId('inspection-state').filter({hasText:labels[state]}).waitFor({timeout:120000});
  const read=await latest(page);assert.equal(read.state,state);return read;
}
function children(){
  return fs.readdirSync('/proc').filter(n=>/^\d+$/.test(n)).flatMap(n=>{
    try{const cmd=fs.readFileSync(`/proc/${n}/cmdline`,'utf8');return cmd.includes('app.services.audio.worker') && cmd.includes('/tmp/ce-r2d-data/cache/managed-rhythm-')?[{pid:Number(n),cmd}]:[];}
    catch(error){if(!['ENOENT','ESRCH','EACCES'].includes(error.code))throw error;return [];}
  });
}
async function liveWorker(){
  const until=Date.now()+15000;
  while(Date.now()<until){const found=children();for(const child of found){try{if(fs.readFileSync(`/proc/${child.pid}/maps`,'utf8').includes('libllvmlite'))return child;}catch(error){if(error.code!=='ENOENT')throw error;}}await new Promise(resolve=>setTimeout(resolve,40));}
  throw Error('No genuine isolated library worker observed');
}
async function measured(page){
  const read=await terminal(page,'done');
  assert.equal(read.operation,'rhythm');assert.equal(read.report.scope,'audio-rhythm-only');assert.equal(read.report.files.length,4);
  for(const file of read.report.files){
    const asset=result.assets.find(a=>a.id===file.asset_id);assert.ok(asset);
    assert.equal(file.sha256,hash(fs.readFileSync(asset.path)));
    if(file.role==='reference'){assert.equal(file.status,'no-audio');assert.equal(file.estimate,null);}
    else if(file.name.includes('None')){assert.equal(file.status,'no-beats');assert.equal(file.estimate.tempo_bpm,null);assert.deepEqual(file.estimate.beat_times_seconds,[]);}
    else{const bpm=file.name.includes('120')?120:90;assert.equal(file.status,'estimated');assert.ok(Math.abs(file.estimate.tempo_bpm-bpm)<5);assert.ok(file.estimate.beat_times_seconds.length>10);}
    if(file.estimate){assert.notEqual(file.sha256,file.estimate.sha256);assert.ok(file.estimate.duration_seconds>11);}
  }
  return read;
}
(async()=>{
  assert.ok(['prepare','reopen','interrupted'].includes(phase));fs.mkdirSync(out,{recursive:true});
  const browser=await pw.launch({executablePath:await chromium.executablePath(),args:chromium.args,headless:true});
  try{
    const page=await browser.newPage({viewport:{width:1920,height:1080}});
    page.on('pageerror',error=>result.errors.push({phase,message:error.message}));
    page.on('request',r=>{
      const parsed=new URL(r.url());if(['http:','https:'].includes(parsed.protocol) && parsed.host!==new URL(base).host)result.external.push(r.url());
      if(r.url().includes('/api/'))result.requests.push({phase,method:r.method(),url:r.url()});
    });
    await page.goto(base);await page.getByRole('button',{name:'زبان',exact:true}).click();
    if(phase==='prepare'){
      result.assets=[];const tasks=[];
      page.on('response',r=>{if(r.url().endsWith('/uploads') && r.status()===201)tasks.push(r.json().then(a=>result.assets.push(a)));});
      await page.getByLabel('Import clips',{exact:true}).setInputFiles([90,120,'None'].map(b=>`/tmp/ce-r2b2-fixtures/owned-${b}.mp4`));
      await page.waitForFunction(()=>document.querySelectorAll('li[data-testid^="clip-"]').length===3,{},{timeout:60000});
      await page.getByLabel('Import reference video',{exact:true}).setInputFiles({name:'مرجع بدون صوت.mp4',mimeType:'video/mp4',buffer:fs.readFileSync('/tmp/ce-media/ref/reference.mp4')});
      await page.getByRole('button',{name:'مرجع بدون صوت.mp4',exact:true}).waitFor();await Promise.all(tasks);
      result.project=result.assets[0].project_id;result.route=`/api/v1/projects/${result.project}/rhythm`;
      await page.getByLabel('Project name',{exact:true}).fill('R2b4 — ضرب‌آهنگ و کش');
      await page.getByRole('button',{name:'Reference intake',exact:true}).click();await panel(page);await saved(page);
      check('Four genuine imported assets, explicit reference/source identity',result.assets.length===4 && result.assets.every(a=>a.project_id===result.project));
      const caps=await(await page.request.get(url(result.route+'/capabilities'))).json();
      check('Experimental local audio available; model analysis still blocked',caps.operation==='rhythm' && caps.inspection.available && !caps.model_analysis.available);
      result.firstJob=(await start(page)).id;
      result.firstWorker=await liveWorker();
      const running=await latest(page);check('Actual library subprocess; stage progress with no premature report',running.state==='running' && running.percent>0 && running.percent<100 && running.report===null,JSON.stringify({pid:result.firstWorker.pid,percent:running.percent,message:running.message}));
      await page.screenshot({path:path.join(out,'01-real-audio-running.png')});
      result.completed=await measured(page);
      check('Real 90/120 BPM estimates, silence, no-audio and independently verified original hashes',true,JSON.stringify(result.completed.report.files.map(f=>({name:f.name,status:f.status,bpm:f.estimate?.tempo_bpm,beats:f.estimate?.beat_times_seconds.length}))));
      await page.screenshot({path:path.join(out,'02-real-audio-results.png')});
      await page.getByRole('button',{name:'Decode verification',exact:true}).click();
      await page.getByText('No saved inspection for this project.',{exact:true}).waitFor();
      check('Decode and rhythm reports cannot be confused',await page.getByTestId('inspection-state').count()===0);
      await panel(page);await terminal(page,'done');await page.reload();await saved(page);await panel(page);await terminal(page,'done');
      check('Reload restores audio report without another start',result.requests.filter(r=>r.method==='POST' && r.url.endsWith('/rhythm/jobs')).length===1);
      const cancelled=await start(page);const child=await liveWorker();
      await page.getByRole('button',{name:'Cancel inspection',exact:true}).click();
      const stop=await terminal(page,'cancelled');
      check('Cancellation reaps genuine librosa worker; no fake report or 100%',stop.id===cancelled.id && stop.report===null && stop.percent<100 && !fs.existsSync(`/proc/${child.pid}`));
      check('Cancellation cleans temporary PCM/result workspace',fs.readdirSync('/tmp/ce-r2d-data/cache').filter(n=>n.startsWith('managed-rhythm-')).length===0);
      const victim=result.assets.find(a=>a.role==='source');const bytes=fs.readFileSync(victim.path);
      try{
        fs.writeFileSync(victim.path,'owned deliberate corrupt container');await start(page);
        const failed=await terminal(page,'failed');
        check('Real ffprobe failure is visible, without estimated results',failed.report===null && failed.percent<100 && !!failed.error);
        await page.screenshot({path:path.join(out,'03-real-audio-failure.png')});
      }finally{fs.writeFileSync(victim.path,bytes);}
      const stale=await latest(page,result.firstJob);check('Restored bytes do not silently renew old provenance',stale.stale && stale.state==='done');
      await start(page);result.completed=await measured(page);await saved(page);
      await page.getByRole('button',{name:'New project',exact:true}).click();await saved(page);await panel(page);
      check('New project has no inherited audio report and cannot start with no inputs',await page.getByTestId('inspection-state').count()===0 && await page.getByRole('button',{name:'Measure audio rhythm',exact:true}).isDisabled());
      const other=await page.evaluate(()=>localStorage.getItem('cutting-edge.last-project'));
      check('Cross-project audio job reads return 404',(await page.request.get(url(`/api/v1/projects/${other}/rhythm/jobs/${result.completed.id}`))).status()===404);
      await choose(page);await terminal(page,'done');
    }else{
      await choose(page);
      if(phase==='reopen'){
        const restored=await measured(page);check('Fresh backend/browser restores same durable report',restored.id===result.completed.id && JSON.stringify(restored.report)===JSON.stringify(result.completed.report));
        result.crashJob=(await start(page)).id;result.crashWorker=await liveWorker();
        const pid=Number(process.env.CE_BACKEND_PID);assert.ok(Number.isInteger(pid)&&pid>1);
        assert.ok(fs.readFileSync(`/proc/${pid}/cmdline`,'utf8').includes('uvicorn'));
        assert.ok(fs.readFileSync(`/proc/${pid}/environ`,'utf8').includes('CUTTING_EDGE_DATA_DIR=/tmp/ce-r2d-data'));
        const wav=result.crashWorker.cmd.split('\0').find(p=>p.includes('/cache/managed-rhythm-') && p.endsWith('/audio.wav'));
        assert.ok(wav);result.crashWorkspace={path:path.dirname(wav),pcm_size:fs.statSync(wav).size,pcm_sha256:hash(fs.readFileSync(wav)),journal:JSON.parse(fs.readFileSync(path.join(path.dirname(wav),'.owner.json')))};
        check('Actual extracted PCM and library PID have registered scratch ownership',result.crashWorkspace.pcm_size>1000 && result.crashWorkspace.journal.child.pid===result.crashWorker.pid);
        const killedAt=Date.now();process.kill(pid,'SIGKILL');
        const until=Date.now()+5000;
        while(fs.existsSync(`/proc/${result.crashWorker.pid}`) && Date.now()<until)await new Promise(resolve=>setTimeout(resolve,50));
        const workerAlive=fs.existsSync(`/proc/${result.crashWorker.pid}`) && !fs.readFileSync(`/proc/${result.crashWorker.pid}/stat`,'utf8').includes(') Z ');
        check('Independent worker guard stops genuine analysis after backend SIGKILL',!workerAlive,`worker PID ${result.crashWorker.pid}; stopped after ${Date.now()-killedAt} ms`);
      }else{
        result.cacheRecovery=(await(await page.request.get(url('/api/v1/system/diagnostics'))).json()).cache_recovery;
        check('Startup recovers actual orphan PCM/library workspace without sweeping unknown cache',result.cacheRecovery.removed===1 && result.cacheRecovery.retained===1 && !fs.existsSync(result.crashWorkspace.path),JSON.stringify(result.cacheRecovery));
        const interrupted=await terminal(page,'interrupted');
        check('Crash recovery marks orphaned job interrupted, never done',interrupted.id===result.crashJob && interrupted.report===null && interrupted.percent<100);
        await page.screenshot({path:path.join(out,'04-crash-interrupted.png')});
        await start(page);result.completed=await measured(page);
        check('Explicit post-crash retry reruns real tools and commits a new report',result.completed.id!==result.crashJob);
        await page.screenshot({path:path.join(out,'05-recovered-real-audio.png')});
        await page.getByRole('button',{name:'Language',exact:true}).click();
        await page.getByText('گزارش صوت ذخیره شد — تحلیل مدل انجام نشده است',{exact:true}).waitFor();
        check('Persian audio labels and RTL render actual recovered results',await page.locator('[dir=rtl]').count()>0);
        await page.screenshot({path:path.join(out,'06-persian-real-audio.png')});
      }
    }
    check('No browser JavaScript errors',result.errors.length===0);
    check('No external browser HTTP requests',result.external.length===0);
    fs.writeFileSync(session,JSON.stringify(result,null,2)+'\n');
    fs.writeFileSync(path.join(out,'real-browser-results.json'),JSON.stringify(result,null,2)+'\n');
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
