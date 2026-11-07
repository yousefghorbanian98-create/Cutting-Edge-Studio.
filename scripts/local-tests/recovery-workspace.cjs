// R1b real browser/backend acceptance, with an actual backend process restart BETWEEN phases.
// Run "prepare", stop/restart the isolated backend with the same SQLite directory, then run "reopen".
// No HTTP mocks. Store imports are used only for inspection and non-exposed trim/track controls.
const chromium = require('@sparticuz/chromium').default;
const { chromium: pw } = require('playwright');
const fs = require('fs');
const path = require('path');
const assert = require('assert/strict');
const out = process.env.CE_E2E_OUTPUT || path.resolve(__dirname, '../../docs/evidence/recovery-r1b');
const runFile = process.env.CE_SESSION_FILE || '/tmp/ce-r1b-run.json';
const storageFile = `${runFile}.browser.json`;
const phase = process.argv[2];
const base = process.env.CE_E2E_UI || 'http://127.0.0.1:1421';
const url = route => new URL(route, base).href;
fs.mkdirSync(out, { recursive:true });
const result = phase === 'prepare' ? { checks:[], requests:[], errors:[], phases:[] } : JSON.parse(fs.readFileSync(runFile));
if (phase === 'reopen') {
  result.checks=result.checks.filter(c=>c.phase!=='reopen');
  result.requests=result.requests.filter(r=>r.phase!=='reopen');
  result.phases=result.phases.filter(p=>p.phase!=='reopen');
}
const check = (name, passed, detail='') => {
  result.checks.push({ phase, name, passed:!!passed, detail });
  console.log(passed?'PASS':'FAIL', name, ...(detail?[detail]:[]));
  if (!passed) throw new Error(`Acceptance failed: ${name}`);
};
async function snapshot(page) {
  return page.evaluate(async () => {
    const { captureSnapshot } = await import('/src/features/workspace/workspaceStore.ts');
    return JSON.parse(JSON.stringify(captureSnapshot()));
  });
}
async function saved(page) {
  // Keep the polling predicate synchronous: a returned Promise is truthy before it resolves.
  await page.waitForFunction(() => document.querySelector('[data-testid="workspace-status"]')?.textContent === 'Saved locally', {}, {timeout:20000});
  const state = await page.evaluate(async () => {
    const {useWorkspaceStore}=await import('/src/features/workspace/workspaceStore.ts');
    const s=useWorkspaceStore.getState();
    return {initialized:s.initialized,dirty:s.dirty,status:s.status,navigating:s.navigating};
  });
  assert.deepStrictEqual(state,{initialized:true,dirty:false,status:'idle',navigating:false});
}
async function read(page, id) { return (await page.request.get(url(`/api/v1/projects/${id}/workspace`))).json(); }
async function chooseProject(page, name, id) {
  await page.getByRole('button',{name:'Refresh projects',exact:true}).click();
  await page.getByRole('combobox',{name:'Open project',exact:true}).waitFor();
  await page.getByRole('combobox',{name:'Open project',exact:true}).click();
  await page.getByRole('option',{name:`${name} · ${id.slice(0,6)}`,exact:true}).click();
}
(async () => {
  if (!['prepare','reopen'].includes(phase)) throw new Error('Expected prepare or reopen phase');
  const browser = await pw.launch({ executablePath:await chromium.executablePath(), args:chromium.args, headless:true });
  let phasePassed=false;
  try {
    const context = await browser.newContext({ viewport:{width:1920,height:1080}, ...(phase==='reopen'?{storageState:storageFile}:{}) });
    context.on('page',page => {
      page.on('pageerror',error => result.errors.push(error.message));
      page.on('request',request => { if (request.url().includes('/api/')) result.requests.push({phase,method:request.method(),url:request.url()}); });
    });
    const page=await context.newPage();
    await page.goto(base);
    if (phase==='prepare') {
      await page.getByRole('button',{name:'زبان',exact:true}).click();
      check('Empty editor does not claim a saved project',await page.getByTestId('workspace-status').textContent()==='No project open');
      const fixtures=[
        { name:'گل اول.mp4', file:'/tmp/ce-media/clips/clip1.mp4', label:'Import clips' },
        { name:'Goal two.mp4', file:'/tmp/ce-media/clips/clip2.mp4', label:'Import clips' },
        { name:'B-roll three.mp4', file:'/tmp/ce-media/clips/clip3.mp4', label:'Import clips' },
        { name:'مرجع.mp4', file:'/tmp/ce-media/ref/reference.mp4', label:'Import reference video' },
      ];
      result.assets=[];
      for (const fixture of fixtures) {
        const response=page.waitForResponse(response => response.url().endsWith('/uploads') && response.status()===201);
        await page.getByLabel(fixture.label,{exact:true}).setInputFiles({name:fixture.name,mimeType:'video/mp4',buffer:fs.readFileSync(fixture.file)});
        result.assets.push(await (await response).json());
        await page.getByRole('button',{name:fixture.name,exact:true}).waitFor();
      }
      result.project=result.assets[0].project_id;
      await page.getByLabel('Project name',{exact:true}).fill('R1b — مسابقهٔ پایدار');
      await page.getByRole('button',{name:'Add to timeline گل اول.mp4',exact:true}).click();
      const ruler=page.getByRole('slider',{name:'playhead',exact:true});
      await ruler.click({position:{x:80,y:10}});
      await page.getByRole('button',{name:'add-bookmark',exact:true}).click();
      await page.getByRole('button',{name:'split',exact:true}).click();
      await page.getByRole('button',{name:'Add to timeline Goal two.mp4',exact:true}).click();
      await page.getByRole('button',{name:'zoom-in',exact:true}).click();
      await page.getByRole('button',{name:'toggle-snap',exact:true}).click();
      await page.getByRole('button',{name:'YouTube',exact:true}).click();
      await page.getByRole('combobox',{name:'Theme',exact:true}).click();
      await page.getByRole('option',{name:'glass',exact:true}).click();
      // No UI exists for track switches or numeric trim yet. Exercise real store actions explicitly.
      await page.evaluate(async (referencePath) => {
        const {useTimelineStore} = await import('/src/features/timeline/timelineStore.ts');
        const timeline=useTimelineStore.getState();
        timeline.trimClip(timeline.clips[1].id,'end',-0.5);
        useTimelineStore.setState({tracks:timeline.tracks.map(track=>({...track,locked:track.id==='v2',muted:track.id==='a1'}))});
        const {useWizardStore}=await import('/src/features/stylematch/wizardStore.ts');
        useWizardStore.getState().selectReference(referencePath);
        useWizardStore.getState().goTo(2);
      }, result.assets[3].path);
      await page.getByRole('button',{name:'گل اول.mp4',exact:true}).click();
      await page.getByRole('button',{name:'Save project',exact:true}).click();
      await saved(page);
      result.expected=await snapshot(page);
      const db=await read(page,result.project);
      assert.deepStrictEqual(db.snapshot,result.expected);
      check('Actual SQLite snapshot matches edited browser stores',db.snapshot.timeline.clips.length===3 && db.snapshot.timeline.bookmarks.length===1);
      check('Split/trim in-points, track flags, zoom, snap, post and reference persist',db.snapshot.timeline.clips[1].inPoint>0 && db.snapshot.timeline.pxPerSecond===50 && !db.snapshot.timeline.snapEnabled && db.snapshot.post.presetId==='youtube' && db.snapshot.referenceAssetId===result.assets[3].id);
      const assets=await (await page.request.get(url(`/api/v1/projects/${result.project}/assets`))).json();
      check('Original Unicode filenames and byte sizes survive backend listing',assets.every(a=>fixtures.some(f=>f.name===a.name) && a.size_bytes>0 && a.available));
      const protectedDelete=await page.request.delete(url(`/api/v1/assets/${result.assets[0].id}`));
      check('Backend rejects deletion of media used in a saved timeline',protectedDelete.status()===409);
      const browserStorage=await page.evaluate(()=>Object.fromEntries(Object.entries(localStorage)));
      check('Browser storage contains only a last-project pointer, not document/media data',Object.keys(browserStorage).length===1 && browserStorage['cutting-edge.last-project']===result.project);
      await page.screenshot({path:path.join(out,'01-saved-workspace.png')});
      await page.reload();
      await saved(page);
      assert.deepStrictEqual(await snapshot(page),result.expected);
      check('Real browser reload restores the complete saved workspace',await page.locator('.timeline-editor-action').count()===3);
      await page.getByRole('button',{name:'New project',exact:true}).click();
      await saved(page);
      check('New project does not inherit old media/timeline',await page.locator('li[data-testid^="clip-"]').count()===0 && await page.locator('.timeline-editor-action').count()===0);
      result.blankProject=await page.evaluate(()=>localStorage.getItem('cutting-edge.last-project'));
      await chooseProject(page,'R1b — مسابقهٔ پایدار',result.project);
      await saved(page);
      assert.deepStrictEqual(await snapshot(page),result.expected);
      check('Project picker reopens the previous SQLite workspace',true);
      const other=await context.newPage();
      await other.goto(base);
      await saved(other);
      await other.getByLabel('Project name',{exact:true}).fill('Concurrent winner');
      await saved(other);
      await page.getByLabel('Project name',{exact:true}).fill('Stale loser');
      await page.getByRole('alert').filter({hasText:'changed elsewhere'}).waitFor();
      check('Two real tabs reject stale saves and retain unsaved local text',await page.getByLabel('Project name').inputValue()==='Stale loser' && (await read(page,result.project)).name==='Concurrent winner');
      check('Conflict prevents automatic overwrite',await page.getByRole('button',{name:'Save project',exact:true}).isDisabled());
      page.once('dialog',dialog=>dialog.accept());
      await page.getByRole('button',{name:'Reopen saved',exact:true}).click();
      await saved(page);
      check('Explicit confirmed reopen recovers the newer tab revision',await page.getByLabel('Project name').inputValue()==='Concurrent winner');
      await other.close();
      await page.getByLabel('Project name').fill('R1b — مسابقهٔ پایدار');
      await saved(page);
      const invalid='{"version":999}';
      await page.request.patch(url(`/api/v1/projects/${result.blankProject}`),{data:{state_json:invalid}});
      await chooseProject(page,'Local editing session',result.blankProject);
      await page.getByRole('alert').filter({hasText:'invalid or unsupported'}).waitFor();
      check('Unsupported saved state is visible and leaves the active editor intact',await page.locator('.timeline-editor-action').count()===3 && await page.getByLabel('Project name').inputValue()==='R1b — مسابقهٔ پایدار');
      const preserved=await (await page.request.get(url(`/api/v1/projects/${result.blankProject}`))).json();
      check('Unsupported saved bytes are not overwritten with defaults',preserved.state_json===invalid);
      await page.getByRole('button',{name:'Reopen saved',exact:true}).click();
      await saved(page);
      const deletionProject=await (await page.request.post(url('/api/v1/projects'),{data:{name:'Deletion recovery check'}})).json();
      const deletedAsset=await (await page.request.post(url(`/api/v1/projects/${deletionProject.id}/uploads`),{multipart:{role:'reference',file:{name:'temporary-reference.mp4',mimeType:'video/mp4',buffer:fs.readFileSync('/tmp/ce-media/ref/reference.mp4')}}})).json();
      const deletionSnapshot=structuredClone(result.expected);
      deletionSnapshot.timeline.clips=[];
      deletionSnapshot.mediaOrder=[deletedAsset.id];
      deletionSnapshot.selectedAssetId=deletedAsset.id;
      deletionSnapshot.referenceAssetId=deletedAsset.id;
      const blank=await read(page,deletionProject.id);
      const savedDeletion=await (await page.request.put(url(`/api/v1/projects/${deletionProject.id}/workspace`),{data:{base_revision:blank.revision,name:'Deletion recovery check',snapshot:deletionSnapshot}})).json();
      const deleted=await page.request.delete(url(`/api/v1/assets/${deletedAsset.id}`));
      assert.equal(deleted.status(),204);
      await chooseProject(page,'Deletion recovery check',deletionProject.id);
      await saved(page);
      await page.getByRole('alert').filter({hasText:'Saved media was deleted'}).waitFor();
      const recoveredDeletion=await snapshot(page);
      check('Deleted unused reference does not make the saved project unopenable',recoveredDeletion.referenceAssetId===null && recoveredDeletion.selectedAssetId===null && recoveredDeletion.timeline.bookmarks.length===1);
      assert.deepStrictEqual(await read(page,deletionProject.id),savedDeletion);
      check('Deletion recovery warns without silently overwriting saved bytes',true);
      await chooseProject(page,'R1b — مسابقهٔ پایدار',result.project);
      await saved(page);
      result.expected=await snapshot(page);
      result.saved=await read(page,result.project);
      result.backendBefore=process.env.CE_BACKEND_PID || 'not recorded';
      await context.storageState({path:storageFile});
      await page.screenshot({path:path.join(out,'02-reopened-and-conflict-recovered.png')});
    } else {
      result.backendAfter=process.env.CE_BACKEND_PID || 'not recorded';
      check('Backend process actually restarted between phases',result.backendBefore!=='not recorded' && result.backendAfter!=='not recorded' && result.backendBefore!==result.backendAfter,`${result.backendBefore} → ${result.backendAfter}`);
      await saved(page);
      assert.deepStrictEqual(await snapshot(page),result.expected);
      assert.deepStrictEqual(await read(page,result.project),result.saved);
      check('New browser process plus restarted backend restores byte-equivalent saved state',true);
      check('Restoring does not re-upload or create replacement projects',result.requests.filter(r=>r.phase==='reopen' && r.method==='POST' && /\/(uploads|projects)$/.test(r.url)).length===0);
      check('All original names reappear after restart',await page.locator('li[data-testid^="clip-"]').count()===4 && await page.getByRole('button',{name:'گل اول.mp4',exact:true}).count()===1);
      await page.waitForFunction(()=>document.querySelector('video')?.readyState>=2,{}, {timeout:15000});
      const player=await page.locator('video').evaluate(v=>({duration:v.duration,src:v.getAttribute('src'),error:v.error?.message}));
      check('Restored source decodes from its original asset-ID route',player.duration>0 && player.src.includes(result.assets[0].id) && !player.error,JSON.stringify(player));
      const content=await page.request.get(url(`/api/v1/assets/${result.assets[0].id}/content`),{headers:{Range:'bytes=0-127'}});
      check('Source streaming remains range-capable after backend restart',content.status()===206 && (await content.body()).length===128);
      const missing=result.assets[2].path;
      fs.renameSync(missing,`${missing}.r1b-backup`);
      try {
        await page.reload();
        await saved(page);
        await page.getByRole('alert').filter({hasText:'Some media files are unavailable'}).waitFor();
        assert.deepStrictEqual(await snapshot(page),result.expected);
        check('Missing managed media produces a warning without discarding saved edits',await page.locator('.timeline-editor-action').count()===3);
        await page.screenshot({path:path.join(out,'03-missing-media-preserves-edits.png')});
      } finally { fs.renameSync(`${missing}.r1b-backup`,missing); }
      await page.reload();
      await saved(page);
      // Sparticuz single-process flags can share storage across contexts; use a NEW browser process.
      const freshBrowser=await pw.launch({executablePath:await chromium.executablePath(),args:chromium.args,headless:true});
      try {
        const fresh=await freshBrowser.newPage({viewport:{width:1920,height:1080}});
        fresh.on('pageerror',error=>result.errors.push(error.message));
        await fresh.goto(base);
        check('Independent empty browser profile has no saved project pointer',await fresh.evaluate(()=>localStorage.getItem('cutting-edge.last-project'))===null);
        if (await fresh.locator('html').getAttribute('lang')!=='en') await fresh.getByRole('button',{name:'زبان',exact:true}).click();
        await chooseProject(fresh,'R1b — مسابقهٔ پایدار',result.project);
        await saved(fresh);
        assert.deepStrictEqual(await snapshot(fresh),result.expected);
        check('An empty browser profile can reopen all document data from SQLite',true);
        await fresh.screenshot({path:path.join(out,'04-recovered-after-real-backend-restart.png')});
      } finally { await freshBrowser.close(); }
      check('No browser page exceptions in either phase',result.errors.length===0,JSON.stringify(result.errors));
    }
    phasePassed=true;
  } finally {
    result.phases.push({phase,passed:phasePassed});
    result.limits=['Source playback only; composited timeline playback/export remains unaccepted.','Numeric trim and track switches were exercised via actual Zustand actions; they have no wired UI controls yet.','No real model analysis, approved render, offline Windows installer or competitor behavior claimed.'];
    fs.writeFileSync(runFile,JSON.stringify(result,null,2));
    fs.writeFileSync(path.join(out,'browser-results.json'),JSON.stringify(result,null,2));
    await browser.close();
  }
})().catch(error=>{console.error('recovery.workspace.test.failed',error);process.exitCode=1;});
