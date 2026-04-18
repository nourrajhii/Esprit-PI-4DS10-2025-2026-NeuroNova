import { bootstrapApplication, BootstrapContext } from '@angular/platform-browser';
import { App } from './app/app';
import { appConfig } from './app/app.config.server';

const bootstrap = (context: BootstrapContext) =>
  bootstrapApplication(App, appConfig, context);

export default bootstrap;