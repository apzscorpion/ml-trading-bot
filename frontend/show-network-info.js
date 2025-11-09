#!/usr/bin/env node
/**
 * Display network access information for the frontend
 */

import { networkInterfaces } from 'os';

function getNetworkIP() {
  const nets = networkInterfaces();
  
  for (const name of Object.keys(nets)) {
    for (const net of nets[name]) {
      // Skip over non-IPv4 and internal (i.e. 127.0.0.1) addresses
      if (net.family === 'IPv4' && !net.internal) {
        return net.address;
      }
    }
  }
  
  return 'Unable to detect';
}

const networkIP = getNetworkIP();
const port = 5155;

console.log('\n' + '='.repeat(70));
console.log('🎨 ML Trading Bot Frontend');
console.log('='.repeat(70));
console.log(`📍 Local Access:   http://localhost:${port}`);
console.log(`📍 Network Access: http://${networkIP}:${port}`);
console.log('');
console.log('📱 Access from other devices on your network:');
console.log(`   Open browser and go to: http://${networkIP}:${port}`);
console.log('='.repeat(70));
console.log('');
console.log('⚡ Starting Vite dev server...\n');

