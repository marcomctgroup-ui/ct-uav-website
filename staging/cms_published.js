/* Published pilot delivery only. Credentials remain in the Pages environment. */
const cmsJson = (data, status=200) => Response.json(data,{status,headers:{
  'Cache-Control':'no-store','X-Content-Type-Options':'nosniff',
  'X-Robots-Tag':'noindex, nofollow','Referrer-Policy':'no-referrer'
}});
export async function readPublishedPilot(request, env) {
  if(request.method!=='GET')return cmsJson({error:'Method not allowed'},405);
  const token=env.STORYBLOK_PUBLIC_TOKEN;
  if(!token)return cmsJson({error:'CMS content is not connected'},503);
  try {
    const url=new URL('https://api.storyblok.com/v2/cdn/stories/decarb-22');
    url.searchParams.set('token',token);url.searchParams.set('version','published');
    const upstream=await fetch(url,{headers:{Accept:'application/json'},signal:AbortSignal.timeout(8000)});
    if(!upstream.ok)return cmsJson({error:'CMS content unavailable'},502);
    const data=await upstream.json(),story=data.story;
    if(Number(story?.id)!==240403768382651||story.content?.component!=='product_page')return cmsJson({error:'CMS content unavailable'},502);
    const content={component:'product_page'};
    for(const key of ['hero_role','hero_role_vi','applications_intro','applications_intro_vi','specifications_table','specifications_table_vi'])content[key]=story.content[key];
    return cmsJson({story:{content}});
  }catch{return cmsJson({error:'CMS content unavailable'},502);}
}
