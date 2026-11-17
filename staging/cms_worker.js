import voiceWorker from './voice-worker.js';
import {readPublishedPilot} from './cms_published.js';
import {servePreview} from './cms_preview.js';
export default {async fetch(request,env,ctx){
  const pathname=new URL(request.url).pathname;
  if(pathname==='/api/cms/decarb22')return readPublishedPilot(request,env);
  if(pathname==='/cms-preview'||pathname.startsWith('/cms-preview/'))return servePreview(request,env);
  return voiceWorker.fetch(request,env,ctx);
}};
