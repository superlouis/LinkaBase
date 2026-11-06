import {cpSync} from 'node:fs';
cpSync('node_modules/@excalidraw/excalidraw/dist/prod/fonts','../editor_dist/fonts',{recursive:true});
