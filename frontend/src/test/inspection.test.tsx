import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useAppStore } from '../store/useAppStore';
import { ApiError } from '../lib/api';
import type * as ApiModule from '../lib/api';
import { InspectionPanel } from '../features/stylematch/InspectionPanel';
import { inspectionSchema } from '../features/stylematch/inspectionSchema';

const calls = vi.hoisted(() => ({capabilities:vi.fn(), latest:vi.fn(), start:vi.fn(), job:vi.fn(), cancel:vi.fn()}));
vi.mock('../lib/api', async original => ({...await original<typeof ApiModule>(), api:{
  inspectionCapabilities:calls.capabilities, latestInspection:calls.latest, startInspection:calls.start,
  getInspection:calls.job, cancelInspection:calls.cancel,
}}));
const capabilities={inspection:{available:true,reason:null},model_analysis:{available:false,reason:'Verified weights and adapters required; no runtime downloads.',unavailable:['StyleDNA'],models_directory:'/fixture/models'}};
const queued={id:'job-fixture',project_id:'project-fixture',reference_asset_id:'reference-fixture',source_asset_ids:['source-fixture'],state:'queued',percent:0,message:'Queued',error:null,stale:false,report:null};
const running={...queued,state:'running',percent:35,message:'Decoding source-fixture.mp4'};
const done={...queued,state:'done',percent:100,report:{version:1,method:'ffprobe+ffmpeg-full-decode',scope:'media-inspection-only',unavailable:['StyleDNA'],files:[{
  asset_id:'source-fixture',role:'source',name:'Measured fixture.mp4',sha256:'a'.repeat(64),size_bytes:123,mtime_ns:'123456',duration:2,width:640,height:360,fps:30,video_codec:'h264',audio_codec:null,has_audio:false,decoded_frames:60,decoded_seconds:2,
}]}};
const props={projectId:'project-fixture',referenceId:'reference-fixture',sourceIds:['source-fixture'],blocked:false};
async function flush(){await act(async()=>{await Promise.resolve();});}
async function tick(){await act(async()=>{await vi.advanceTimersByTimeAsync(500);});}
async function start(){fireEvent.click(screen.getByRole('button',{name:'Inspect media (decode)'}));await flush();}

beforeEach(()=>{
  useAppStore.setState({language:'en'});
  vi.useFakeTimers();
  vi.clearAllMocks();
  calls.capabilities.mockResolvedValue(capabilities);
  calls.latest.mockRejectedValue(new ApiError('No inspection exists',404));
  calls.start.mockResolvedValue(queued);
  calls.job.mockResolvedValue(running);
  calls.cancel.mockResolvedValue({...running,message:'Cancelling'});
});
afterEach(()=>{vi.useRealTimers();});

describe('media inspection panel — fixtures only, no inferred sports/DNA claims',()=>{
  it('shows honest scope and blocked model work before any job exists',async()=>{
    render(<InspectionPanel {...props}/>);await flush();
    expect(screen.getByRole('button',{name:'Inspect media (decode)'})).toBeEnabled();
    expect(screen.getByText(/This is NOT model analysis, beats, StyleDNA/)).toBeInTheDocument();
    expect(screen.getByText(/verified pretrained weights and wired adapters/)).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(calls.start).not.toHaveBeenCalled();
  });
  it('submits registered IDs and displays only observed server progress and measured results',async()=>{
    render(<InspectionPanel {...props}/>);await flush();await start();
    expect(calls.start).toHaveBeenCalledWith('project-fixture','reference-fixture',['source-fixture']);
    expect(screen.getByText('Inspection queued')).toBeInTheDocument();
    expect(screen.queryByText(/Measured fixture.mp4/)).not.toBeInTheDocument();
    await tick();
    expect(screen.getByText('Inspecting actual media')).toBeInTheDocument();
    expect(screen.getByText('Decoding source-fixture.mp4')).toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow','35');
    calls.job.mockResolvedValue(done);await tick();
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow','100');
    expect(screen.getByText('Media decode verified — model analysis not performed')).toBeInTheDocument();
    expect(screen.getByText(/Measured fixture.mp4/)).toBeInTheDocument();
    expect(screen.getByText(/60 frames/)).toBeInTheDocument();
    expect(screen.queryByRole('button',{name:'Cancel inspection'})).not.toBeInTheDocument();
    const count=calls.job.mock.calls.length;await tick();expect(calls.job).toHaveBeenCalledTimes(count);
  });
  it('requests cancellation without pretending it completed before the worker confirms',async()=>{
    calls.latest.mockResolvedValue(running);
    render(<InspectionPanel {...props}/>);await flush();
    fireEvent.click(screen.getByRole('button',{name:'Cancel inspection'}));await flush();
    expect(calls.cancel).toHaveBeenCalledWith('project-fixture','job-fixture');
    expect(screen.getByText('Inspecting actual media')).toBeInTheDocument();
    calls.job.mockResolvedValue({...running,state:'cancelled',message:'cancelled'});await tick();
    expect(screen.getByText('Inspection cancelled')).toBeInTheDocument();
    expect(screen.queryByText(/Measured fixture.mp4/)).not.toBeInTheDocument();
  });
  it('renders decoder failures and allows an explicit retry',async()=>{
    calls.latest.mockResolvedValue({...queued,state:'failed',error:'FFprobe could not read this file'});
    render(<InspectionPanel {...props}/>);await flush();
    expect(screen.getByRole('alert')).toHaveTextContent('FFprobe could not read this file');
    expect(screen.getByRole('button',{name:'Inspect media (decode)'})).toBeEnabled();
    await start();expect(screen.getByText('Inspection queued')).toBeInTheDocument();
  });
  it('does not replace a failed poll with synthetic success, and refresh restores polling',async()=>{
    calls.latest.mockResolvedValue(running);calls.job.mockRejectedValue(new Error('Backend unavailable'));
    render(<InspectionPanel {...props}/>);await flush();await tick();
    expect(screen.getByRole('alert')).toHaveTextContent('Backend unavailable');
    expect(screen.getByText('Inspecting actual media')).toBeInTheDocument();
    const count=calls.job.mock.calls.length;await tick();expect(calls.job).toHaveBeenCalledTimes(count);
    calls.latest.mockResolvedValue(done);
    fireEvent.click(screen.getByRole('button',{name:'Refresh inspection'}));await flush();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.getByText('Media decode verified — model analysis not performed')).toBeInTheDocument();
  });
  it('blocks missing inputs and missing tools rather than inventing results',async()=>{
    calls.capabilities.mockResolvedValue({...capabilities,inspection:{available:false,reason:'Pinned bundled FFmpeg missing'}});
    render(<InspectionPanel {...props} blocked/>);await flush();
    expect(screen.getByRole('alert')).toHaveTextContent('Pinned bundled FFmpeg missing');
    expect(screen.getByRole('button',{name:'Inspect media (decode)'})).toBeDisabled();
    expect(calls.start).not.toHaveBeenCalled();
  });
  it('warns when the current reference/source selection differs from the persisted job',async()=>{
    calls.latest.mockResolvedValue(done);
    const view=render(<InspectionPanel {...props}/>);await flush();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    view.rerender(<InspectionPanel {...props} referenceId="another-reference"/>);
    expect(screen.getByRole('alert')).toHaveTextContent(/Inputs changed or are unavailable/);
  });
  it('warns on backend-detected file changes even with identical IDs',async()=>{
    calls.latest.mockResolvedValue({...done,stale:true});
    render(<InspectionPanel {...props}/>);await flush();
    expect(screen.getByRole('alert')).toHaveTextContent(/Inputs changed or are unavailable/);
  });
  it('does not leak an old project response after keyed project navigation',async()=>{
    let resolveOld: (value:unknown)=>void=()=>{};
    calls.latest.mockImplementationOnce(()=>new Promise(resolve=>{resolveOld=resolve;}));
    const view=render(<InspectionPanel key="old" {...props}/>);await flush();
    const signal=calls.latest.mock.calls[0]![1] as AbortSignal;
    view.rerender(<InspectionPanel key="new" {...props} projectId="project-new"/>);await flush();
    expect(signal.aborted).toBe(true);
    await act(async()=>{resolveOld(done);});
    expect(screen.queryByText(/Measured fixture.mp4/)).not.toBeInTheDocument();
    calls.start.mockResolvedValue({...queued,project_id:'project-new'});
    await start();expect(calls.start).toHaveBeenCalledWith('project-new','reference-fixture',['source-fixture']);
  });
  it('ignores an old start response after leaving the project',async()=>{
    let resolveOld: (value:unknown)=>void=()=>{};
    calls.start.mockImplementationOnce(()=>new Promise(resolve=>{resolveOld=resolve;}));
    const view=render(<InspectionPanel key="old" {...props}/>);await flush();await start();
    view.rerender(<InspectionPanel key="new" {...props} projectId="project-new"/>);await flush();
    await act(async()=>{resolveOld(done);});
    expect(screen.queryByText(/Measured fixture.mp4/)).not.toBeInTheDocument();
  });
  it('rejects malformed success-shaped responses instead of showing completion',async()=>{
    calls.latest.mockResolvedValue({...done,report:null});
    render(<InspectionPanel {...props}/>);await flush();
    expect(screen.getByRole('alert')).toHaveTextContent(/no committed measured report/);
    expect(screen.queryByText('Media decode verified — model analysis not performed')).not.toBeInTheDocument();
    expect(inspectionSchema.safeParse({...done,percent:20}).success).toBe(false);
    expect(inspectionSchema.safeParse({...done,report:{...done.report,scope:'style-dna'}}).success).toBe(false);
  });
});
