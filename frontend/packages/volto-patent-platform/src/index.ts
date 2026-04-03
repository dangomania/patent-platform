import type { ConfigType } from '@plone/registry';
import installSettings from './config/settings';
import CaseView from './components/Case/CaseView';
import JobView from './components/Job/JobView';
import OAView from './components/OfficeAction/OAView';
import Dashboard from './components/Dashboard/Dashboard';
import AntecedentChecker from './components/Tools/AntecedentChecker';
import MultiClaimChecker from './components/Tools/MultiClaimChecker';
import TranslationChecker from './components/Tools/TranslationChecker';
import DictionaryManager from './components/TranslationRule/DictionaryManager';

function applyConfig(config: ConfigType) {
  installSettings(config);

  // Register content type views
  config.views.contentTypesViews = {
    ...config.views.contentTypesViews,
    PatentCase: CaseView,
    PatentJob: JobView,
    OfficeAction: OAView,
  };

  // Register custom routes
  config.addonRoutes = [
    ...(config.addonRoutes || []),
    { path: '/dashboard', component: Dashboard, exact: true },
    { path: '/tools/antecedent', component: AntecedentChecker, exact: true },
    { path: '/tools/multi-claim', component: MultiClaimChecker, exact: true },
    { path: '/tools/translation-check', component: TranslationChecker, exact: true },
    { path: '/dictionary', component: DictionaryManager, exact: true },
  ];

  return config;
}

export default applyConfig;
