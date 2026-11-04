// R2b3 real native FFmpeg scdet candidate acceptance. No mocked API or measurement responses.
// Owned fixtures, external test libraries and test-only socket guard are NOT bundled.
const chromium=require('@sparticuz/chromium').default;
const {chromium:pw}=require('playwright');
const fs=require('fs');
const path=require('path');
const crypto=require('crypto');
const assert=require('assert/strict');
const phase=process.argv[2];
const base=process.env.CE_E2E_UI || 'http://127.0.0.1:1421';
const out=process.env.CE_E2E_OUTPUT || path.resolve(__dirname,'../../docs/evidence/recovery-r2b3');
const session='/tmp/ce-r2c-run.json';
const result=phase==='prepare'?{checks:[],errors:[],external:[],requests:[],limits:[
  'Diagnostic Linux LGPL shared tools, NOT approved Windows shipping runtime.',
  'Native threshold cut candidates only, NOT semantic shots, pretrained inference, StyleDNA or export.',
  'Percentages are observed hash/probe/file stages, NOT detector iterations or ETA.',
  'Native-child crash supervision and orphan-hardlink GC remain OPEN.',
]}:JSON.parse(fs.readFileSync(session));
const url=route=>new URL(route,base).href;
const hash=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
function check(name,passed,detail=''){result.checks.push({phase,name,passed:!!passed,detail});console.log(passed?'PASS':'FAIL',name,detail);assert.ok(passed,name);}
async function saved(page){await page.waitForFunction(()=>document.querySelector('[data-testid="workspace-status"]')?.textContent==='Saved locally',{},{timeout:20000});}
async function panel(page){
  await page.getByRole('button',{name:'3. Clip analysis',exact:true}).click();
  await page.getByRole('button',{name:'Cut candidates (experimental)',exact:true}).click();
  await page.getByRole('button',{name:'Measure cut candidates',exact:true}).waitFor();
}
async function choose(page){
  await page.getByRole('button',{name:'Refresh projects',exact:true}).click();
  await page.getByRole('combobox',{name:'Open project',exact:true}).click();
  await page.getByRole('option',{name:`R2b3 — کاندید واقعی برش · ${result.project.slice(0,6)}`,exact:true}).click();
  await saved(page);await panel(page);
}
async function latest(page,job){const r=await page.request.get(url(result.route+(job?`/jobs/${job}`:'/latest')));assert.equal(r.status(),200);return r.json();}
async function start(page){
  const posted=page.waitForResponse(r=>r.url().endsWith('/scenes/jobs') && r.request().method()==='POST' && r.status()===202);
  await page.getByRole('button',{name:'Measure cut candidates',exact:true}).click();
  return (await posted).json();
}
async function terminal(page,state){
  const labels={done:'Candidate report saved — model analysis not performed',cancelled:'Cut candidate job cancelled',failed:'Cut candidate measurement failed',interrupted:'Cut candidate job interrupted by backend restart'};
  await page.getByTestId('inspection-state').filter({hasText:labels[state]}).waitFor({timeout:120000});
  const read=await latest(page);assert.equal(read.state,state);return read;
}
function children(){
  return fs.readdirSync('/proc').filter(n=>/^\d+$/.test(n)).flatMap(n=>{
    try{const cmd=fs.readFileSync(`/proc/${n}/cmdline`,'utf8');
      if(!cmd.includes('movie=filename=input:'))return [];
      const cwd=fs.readlinkSync(`/proc/${n}/cwd`);
      return cwd.startsWith('/tmp/ce-r2c-data/cache/scenes-')?[{pid:Number(n),cmd,cwd}]:[];
    }catch(error){if(!['ENOENT','ESRCH','EACCES','EINVAL'].includes(error.code))throw error;return [];}
  });
}
async function liveWorker(){
  const until=Date.now()+15000;
  while(Date.now()<until){const found=children();if(found.length)return found[0];await new Promise(resolve=>setTimeout(resolve,40));}
  throw Error('No genuine isolated native scdet process observed');
}
async function measured(page){
  const read=await terminal(page,'done');
  assert.equal(read.operation,'scenes');assert.equal(read.report.scope,'shot-candidates-only');assert.equal(read.report.files.length,4);
  for(const file of read.report.files){
    const asset=result.assets.find(a=>a.id===file.asset_id);assert.ok(asset);
    assert.equal(file.sha256,hash(fs.readFileSync(asset.path)));
    if(file.name.endsWith('.wav')){assert.equal(file.status,'no-video');assert.equal(file.estimate,null);}
    else if(file.name.includes('cuts-audio-first')){
      assert.equal(file.status,'candidates');assert.equal(file.estimate.frames_analyzed,120);
      assert.deepEqual(file.estimate.candidates.map(c=>c.time_seconds),[1,3]);
      assert.deepEqual(file.estimate.candidates.map(c=>c.frame_index),[30,90]);assert.ok(file.has_audio);
    }else{assert.equal(file.status,'no-candidates');assert.deepEqual(file.estimate.candidates,[]);
      assert.equal(file.estimate.frames_analyzed,file.role==='reference'?600:60);}
    if(file.estimate)assert.equal(file.estimate.time_origin,'first-decoded-video-frame');
  }
  return read;
}
(async()=>{
  assert.ok(['prepare','reopen','interrupted','verify'].includes(phase));fs.mkdirSync(out,{recursive:true});
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
      await page.getByLabel('Import clips',{exact:true}).setInputFiles(['owned-cuts-audio-first.mp4','owned-static.mp4','owned-audio-only.wav'].map(n=>'/tmp/ce-r2c-fixtures/'+n));
      await page.waitForFunction(()=>document.querySelectorAll('li[data-testid^="clip-"]').length===3,{},{timeout:60000});
      await page.getByLabel('Import reference video',{exact:true}).setInputFiles({name:'مرجع بدون صوت.mp4',mimeType:'video/mp4',buffer:fs.readFileSync('/tmp/ce-media/ref/reference.mp4')});
      await page.getByRole('button',{name:'مرجع بدون صوت.mp4',exact:true}).waitFor();await Promise.all(tasks);
      result.project=result.assets[0].project_id;result.route=`/api/v1/projects/${result.project}/scenes`;
      await page.getByLabel('Project name',{exact:true}).fill('R2b3 — کاندید واقعی برش');
      await page.getByRole('button',{name:'Reference intake',exact:true}).click();await panel(page);await saved(page);
      check('Four genuine imported assets, explicit reference/source identity',result.assets.length===4 && result.assets.every(a=>a.project_id===result.project));
      const caps=await(await page.request.get(url(result.route+'/capabilities'))).json();
      check('Experimental local scdet available; model analysis still blocked',caps.operation==='scenes' && caps.inspection.available && !caps.model_analysis.available);
      result.firstJob=(await start(page)).id;
      result.firstWorker=await liveWorker();
      const running=await latest(page);check('Actual native scdet subprocess; file-stage progress with no premature report',running.state==='running' && running.percent>0 && running.percent<100 && running.report===null,JSON.stringify({pid:result.firstWorker.pid,percent:running.percent,message:running.message}));
      await page.screenshot({path:path.join(out,'01-real-candidates-running.png')});
      result.completed=await measured(page);
      check('Real cuts at 1s/3s, audio-first video stream, static/no-video and matching original hashes',true,JSON.stringify(result.completed.report.files.map(f=>({name:f.name,status:f.status,frames:f.estimate?.frames_analyzed,times:f.estimate?.candidates.map(c=>c.time_seconds)}))));
      await page.screenshot({path:path.join(out,'02-real-candidates-results.png')});
      await page.getByRole('button',{name:'Decode verification',exact:true}).click();
      await page.getByText('No saved inspection for this project.',{exact:true}).waitFor();
      check('Decode and candidate reports cannot be confused',await page.getByTestId('inspection-state').count()===0);
      await panel(page);await terminal(page,'done');await page.reload();await saved(page);await panel(page);await terminal(page,'done');
      check('Reload restores candidate report without another start',result.requests.filter(r=>r.method==='POST' && r.url.endsWith('/scenes/jobs')).length===1);
      const cancelled=await start(page);const child=await liveWorker();
      await page.getByRole('button',{name:'Cancel inspection',exact:true}).click();
      const stop=await terminal(page,'cancelled');
      check('Cancellation reaps genuine native decoder; no fake report or 100%',stop.id===cancelled.id && stop.report===null && stop.percent<100 && !fs.existsSync(`/proc/${child.pid}`));
      check('Cancellation removes temporary hardlink workspace',fs.readdirSync('/tmp/ce-r2c-data/cache').filter(n=>n.startsWith('scenes-')).length===0);
      const victim=result.assets.find(a=>a.role==='source');const bytes=fs.readFileSync(victim.path);
      try{
        fs.writeFileSync(victim.path,'owned deliberate corrupt container');await start(page);
        const failed=await terminal(page,'failed');
        check('Real ffprobe failure is visible, without estimated results',failed.report===null && failed.percent<100 && !!failed.error);
        await page.screenshot({path:path.join(out,'03-real-candidates-failure.png')});
      }finally{fs.writeFileSync(victim.path,bytes);}
      const stale=await latest(page,result.firstJob);check('Restored bytes do not silently renew old provenance',stale.stale && stale.state==='done');
      await start(page);result.completed=await measured(page);await saved(page);
      await page.getByRole('button',{name:'New project',exact:true}).click();await saved(page);await panel(page);
      check('New project has no inherited candidate report and cannot start with no inputs',await page.getByTestId('inspection-state').count()===0 && await page.getByRole('button',{name:'Measure cut candidates',exact:true}).isDisabled());
      const other=await page.evaluate(()=>localStorage.getItem('cutting-edge.last-project'));
      check('Cross-project candidate job reads return 404',(await page.request.get(url(`/api/v1/projects/${other}/scenes/jobs/${result.completed.id}`))).status()===404);
      await choose(page);await terminal(page,'done');
    }else{
      await choose(page);
      if(phase==='verify'){
        const previous=result.completed.id;await start(page);result.completed=await measured(page);
        check('Final code reruns real native detection with unchanged candidate truth and source hashes',result.completed.id!==previous);
        await page.screenshot({path:path.join(out,'07-final-code-candidates-english.png')});
        await page.getByRole('button',{name:'Language',exact:true}).click();
        await page.getByText('گزارش کاندیدها ذخیره شد — تحلیل مدل انجام نشده است',{exact:true}).waitFor();
        await page.screenshot({path:path.join(out,'08-final-code-candidates-persian.png')});
      }else if(phase==='reopen'){
        const restored=await measured(page);check('Fresh backend/browser restores same durable report',restored.id===result.completed.id && JSON.stringify(restored.report)===JSON.stringify(result.completed.report));
        result.crashJob=(await start(page)).id;result.crashWorker=await liveWorker();
        const pid=Number(process.env.CE_BACKEND_PID);assert.ok(Number.isInteger(pid)&&pid>1);
        assert.ok(fs.readFileSync(`/proc/${pid}/cmdline`,'utf8').includes('uvicorn'));
        assert.ok(fs.readFileSync(`/proc/${pid}/environ`,'utf8').includes('CUTTING_EDGE_DATA_DIR=/tmp/ce-r2c-data'));
        const killedAt=Date.now();process.kill(pid,'SIGKILL');
        await new Promise(resolve=>setTimeout(resolve,200));
        const child=children().find(c=>c.pid===result.crashWorker.pid);
        result.crashObservation={elapsed_ms:Date.now()-killedAt,native_alive_after_parent_kill:!!child,
          orphan_workspace_present:fs.existsSync(result.crashWorker.cwd),qa_cleanup_native_process:false};
        // Explicit QA-only cleanup, NOT product crash supervision. No false guard PASS.
        if(child){process.kill(child.pid,'SIGKILL');result.crashObservation.qa_cleanup_native_process=true;}
        console.log('KNOWN OPEN CRASH LIMIT',JSON.stringify(result.crashObservation));
      }else{
        const interrupted=await terminal(page,'interrupted');
        check('Crash recovery marks orphaned job interrupted, never done',interrupted.id===result.crashJob && interrupted.report===null && interrupted.percent<100);
        await page.screenshot({path:path.join(out,'04-crash-interrupted.png')});
        await start(page);result.completed=await measured(page);
        check('Explicit post-crash retry reruns real tools and commits a new report',result.completed.id!==result.crashJob);
        await page.screenshot({path:path.join(out,'05-recovered-real-candidates.png')});
        await page.getByRole('button',{name:'Language',exact:true}).click();
        await page.getByText('گزارش کاندیدها ذخیره شد — تحلیل مدل انجام نشده است',{exact:true}).waitFor();
        check('Persian candidate labels and RTL render actual recovered results',await page.locator('[dir=rtl]').count()>0);
        await page.screenshot({path:path.join(out,'06-persian-real-candidates.png')});
      }
    }
    result.sourceFilesAtFinalVerification=phase==='verify'?Object.fromEntries(['backend/app/services/media/scenes.py','backend/app/schemas_scenes.py','frontend/src/features/stylematch/InspectionPanel.tsx'].map(p=>[p,hash(fs.readFileSync(path.resolve(__dirname,'../..',p)))])):result.sourceFilesAtFinalVerification;
    check('No browser JavaScript errors',result.errors.length===0);
    check('No external browser HTTP requests',result.external.length===0);
    fs.writeFileSync(session,JSON.stringify(result,null,2)+'\n');
    fs.writeFileSync(path.join(out,'real-browser-results.json'),JSON.stringify(result,null,2)+'\n');
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
