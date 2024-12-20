import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  // Handle WebSocket upgrade requests
  if (request.nextUrl.pathname === '/ws') {
    const url = request.nextUrl.clone()
    url.protocol = 'ws:'
    url.hostname = 'localhost'
    url.port = '8000'
    
    return NextResponse.rewrite(url, {
      headers: {
        'Upgrade': 'websocket',
        'Connection': 'Upgrade',
      },
    })
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/ws', '/api/:path*'],
}