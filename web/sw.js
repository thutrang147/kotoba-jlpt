'use strict';
// Network only: never store authentication, progress, answers or old app bundles.
self.addEventListener('install',event=>event.waitUntil(self.skipWaiting()));
self.addEventListener('activate',event=>event.waitUntil(self.clients.claim()));
self.addEventListener('fetch',event=>{
  if(event.request.mode==='navigate')event.respondWith(fetch(event.request).catch(()=>new Response(
    '<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Kotoba JLPT N3</title><h1>Đang mất kết nối</h1><p>Kotoba cần mạng để lưu tiến trình. Hãy kết nối Internet rồi mở lại ứng dụng.</p><a href="/">Thử lại</a></html>',
    {status:503,headers:{'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-store'}})));
});
