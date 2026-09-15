/* Optional browser acceptance: requires Playwright, Chromium and Python.
 * ROUTING_FLOW_PYTHON selects a Python interpreter; CHROMIUM_EXECUTABLE selects
 * an installed browser. Runs the actual packaged shell with fixture API data.
 */
const fs = require('node:fs');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
const generated = spawnSync(process.env.ROUTING_FLOW_PYTHON || 'python3', ['-c', `import sys,json;sys.path.insert(0,'src');from webui.service import WebUIService;C=type('C',(),{'get':lambda self,*a,default=None:default});s=WebUIService(C());print(json.dumps({'html':s.response('/').body.decode(),'assets':s.assets}))`], {cwd:root,encoding:'utf8'});
if(generated.status!==0)throw Error(generated.stderr);
const packaged=JSON.parse(generated.stdout);
const fixture=JSON.parse(fs.readFileSync(path.join(root,'tests/fixtures/routing_flow.json')));
(async()=>{
 const options={headless:true};
 if(process.env.CHROMIUM_EXECUTABLE)options.executablePath=process.env.CHROMIUM_EXECUTABLE;
 options.args=['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'];
 const browser=await chromium.launch(options);
 const page=await browser.newPage({viewport:{width:1600,height:1100},reducedMotion:'reduce'});
 const errors=[],writes=[],requests=[];let fail=false,requestCount=0,authFail=false,delay=0;
 page.on('pageerror',e=>errors.push(e.message));
 await page.route('http://nowlert.test/**',async route=>{
  const req=route.request(),url=new URL(req.url()),p=url.pathname;
  if(!['GET','HEAD'].includes(req.method()))writes.push(p);
  if(p==='/'){return route.fulfill({contentType:'text/html',body:packaged.html,headers:{'Content-Security-Policy':"default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'self'"}})}
  if(packaged.assets[p]){const [file,type]=packaged.assets[p];return route.fulfill({contentType:type,body:fs.readFileSync(path.join(root,file))});}
  if(!p.startsWith('/api/'))return route.fulfill({status:404,body:''});
  requests.push(p);let value={};
  if(p.includes('/routing-flow/')){
   requestCount++;if(delay)await new Promise(r=>setTimeout(r,delay));
   if(authFail)return route.fulfill({status:401,json:{error:'session expired'}});
   if(fail)return route.fulfill({status:503,json:{error:'unavailable'}});
   value=structuredClone(fixture);value.generated_at=Math.floor(Date.now()/1000);value.range=p.split('/').pop();
   value.metrics.delivered+=requestCount;value.history[0].id='fresh-'+requestCount;value.history[0].completed_at=value.generated_at;
  }else if(p.endsWith('/bootstrap'))value={required:false};
  else if(p.endsWith('/session'))value={user:{id:'browser-user',username:'ruben',role:'user'},csrf_token:'fixture',expires_at:Math.floor(Date.now()/1000)+3600};
  else if(p.endsWith('/integrations'))value={integrations:fixture.routes.map(r=>({source:r.source,name:r.integration_name,inputs:[{key:r.input_type,name:r.input_type}],enabled:true})),route_options:[]};
  else if(p.endsWith('/integration-settings'))value={settings:{},errors:[]};
  else if(p.endsWith('/destinations'))value={destinations:[]};
  else if(p.endsWith('/routes'))value={routes:[]};
  else if(p.endsWith('/tokens'))value={tokens:[]};
  else if(p.includes('/deliveries'))value={deliveries:[],pagination:{page:1,page_size:25,total:0,total_pages:1}};
  else if(p.includes('/audit-events'))value={audit_events:[],pagination:{page:1,page_size:25,total:0,total_pages:1}};
  else if(p.endsWith('/preferences'))value={preferences:{language:'en-GB',timezone:'UTC',time_format:'24',date_format:'DD/MM/YYYY'}};
  else if(p.includes('/metrics/'))value={metrics:{sources:0,destinations:0,routes:0,applications:0,requests:0,delivered:0,success_percent:null}};
  else if(p.endsWith('/version'))value={version:{running:'3.1.2',latest:'3.1.2'}};
  else if(p.endsWith('/filters'))value={filters:[],destinations:[]};
  return route.fulfill({json:value});
 });
 await page.goto('http://nowlert.test/#routing-flow');
 await page.locator('.rf-route').first().waitFor();
 assert.equal(await page.locator('#primary-nav [data-view="routing-flow"]').count(),1);
 assert.equal(await page.locator('#primary-nav [data-view="sources"]').count(),0);
 assert.equal(await page.locator('#primary-nav [data-view="routes"]').count(),0);
 assert.equal(await page.locator('.rf-route').count(),6);
 assert.equal(await page.locator('#page-title').innerText(),'Routing Flow','Header follows new menu after regional translation');
 assert.equal(await page.locator('.rf-filter').count(),7);
 assert.equal(await page.locator('.rf-destination').count(),3);
 assert.equal(await page.locator('.rf-metric').nth(0).innerText(),'—\nReceived\nNot recorded');
 await page.locator('.rf-route').filter({hasText:'Grafana'}).click();
 assert.match(await page.locator('.rf-dialog').innerText(),/cpu\*/);
 assert.match(await page.locator('.rf-dialog').innerText(),/disk\*/);
 await page.locator('.rf-dialog button').click();
 await page.locator('#rf-pause').click();const pausedAt=requestCount;
 await page.waitForTimeout(5200);assert.equal(requestCount,pausedAt,'Pause must stop requests');
 await page.locator('#rf-minus').click();assert.equal(await page.locator('#rf-zoom-value').innerText(),'90%');
 await page.locator('#rf-fit').click();assert.equal(await page.locator('#rf-zoom-value').innerText(),'100%');
 await page.locator('#rf-range').selectOption('1h');assert.equal(requestCount,pausedAt);
 await page.locator('#rf-pause').click();await page.waitForFunction(()=>document.querySelectorAll('.rf-route').length===6);
 await page.waitForTimeout(200);assert.equal(requests.filter(p=>p.includes('routing-flow')).at(-1),'/api/v2/routing-flow/1h');
 fail=true;await page.locator('#rf-range').selectOption('1d');await page.locator('#rf-error').waitFor();assert.match(await page.locator('#rf-error').innerText(),/503/);
 fail=false;await page.locator('#rf-range').selectOption('15m');await page.locator('.rf-route').first().waitFor();
 await page.locator('#rf-pause').click();
 const failedImages=await page.locator('#view-routing-flow img').evaluateAll(es=>es.filter(e=>!e.complete||!e.naturalWidth).map(e=>e.src));assert.deepEqual(failedImages,[]);
 for(const width of [1600,1024,736,390]){
  await page.setViewportSize({width,height:1100});await page.waitForTimeout(150);
  const overflow=await page.locator('#view-routing-flow').evaluate(e=>e.scrollWidth>e.clientWidth+1);assert.equal(overflow,false,'View overflow at '+width);
 }
 await page.setViewportSize({width:1600,height:1100});await page.waitForTimeout(200);
 if(process.env.ROUTING_FLOW_SCREENSHOT)await page.screenshot({path:process.env.ROUTING_FLOW_SCREENSHOT,fullPage:true});
 // Verify particles against new real-shaped attempt IDs, not initial history.
 await page.emulateMedia({reducedMotion:'no-preference'});
 await page.locator('#rf-pause').click();
 await page.locator('.rf-particle').first().waitFor({state:'attached'});
 await page.waitForTimeout(1800);assert.equal(await page.locator('.rf-particle').count(),0,'Particles expire');
 await page.locator('#rf-pause').click();assert.equal(await page.locator('.rf-particle').count(),0,'Pause clears particles');
 await page.emulateMedia({reducedMotion:'reduce'});
 await page.locator('#rf-pause').click();await page.waitForTimeout(200);
 assert.equal(await page.locator('.rf-particle').count(),0,'Reduced motion prevents particles');
 await page.evaluate(()=>{Object.defineProperty(document,'hidden',{configurable:true,value:true});document.dispatchEvent(new Event('visibilitychange'));});
 const hiddenAt=requestCount;await page.waitForTimeout(5200);assert.equal(requestCount,hiddenAt,'Hidden tab must stop polling');
 await page.evaluate(()=>{delete document.hidden;document.dispatchEvent(new Event('visibilitychange'));});
 await page.waitForTimeout(250);assert.ok(requestCount>hiddenAt,'Visible tab refreshes');
 await page.locator('#rf-pause').click();
 await page.evaluate(()=>navigate('dashboard'));const leftAt=requestCount;
 await page.waitForTimeout(5200);assert.equal(requestCount,leftAt,'Inactive view must not poll');
 // A delayed response from the old range must not repopulate a paused/cleared view.
 await page.evaluate(()=>navigate('routing-flow'));delay=400;
 await page.locator('#rf-pause').click();await page.locator('#rf-range').selectOption('1h');await page.locator('#rf-pause').click();
 await page.waitForTimeout(600);assert.equal(await page.locator('.rf-route').count(),0,'Stale response discarded');
 delay=0;authFail=true;await page.locator('#rf-pause').click();await page.locator('#login-view').waitFor();assert.equal(await page.locator('.rf-route').count(),0,'Logout clears data');
 assert.deepEqual(writes,[],'Read-only overview must not issue mutations');
 assert.deepEqual(errors,[],'No browser runtime errors');
 console.log('PASS: actual shell navigation, retired menus, 6 routes/7 destination filters/3 destinations, brand images, details, ranges, pause, zoom, failed requests, stale responses, logout, read-only traffic and responsive layout.');
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
