export type Language = 'fa' | 'en';
export type Direction = 'rtl' | 'ltr';

type Dict = Record<string, string>;

const fa: Dict = {
  'app.title': 'کاتینگ اج v2',
  'app.subtitle': 'ویرایشگر ویدیوی ورزشی',
  'menu.file': 'فایل',
  'menu.edit': 'ویرایش',
  'menu.view': 'نمایش',
  'menu.ai': 'هوش مصنوعی',
  'menu.help': 'راهنما',
  'panel.media': 'رسانه',
  'panel.preview': 'پیش‌نمایش',
  'panel.properties': 'خصوصیات',
  'panel.timeline': 'تایم‌لاین',
  'media.empty': 'هنوز کلیپی وارد نشده است',
  'media.import': 'ورود کلیپ',
  'preview.empty': 'برای شروع، ۱۰ کلیپ و یک رفرنس وارد کنید',
  'timeline.empty': 'تایم‌لاین خالی است',
  'status.backend.online': 'هستهٔ پردازش متصل است',
  'status.backend.offline': 'هستهٔ پردازش در دسترس نیست',
  'status.offline.mode': 'حالت آفلاین',
  'status.version': 'نسخه',
  'wizard.title': 'تطبیق سبک',
  'wizard.step.1': 'ورود رفرنس',
  'wizard.step.2': 'استخراج DNA',
  'wizard.step.3': 'تحلیل کلیپ‌ها',
  'wizard.step.4': 'بررسی سازگاری',
  'wizard.step.5': 'ساخت EDL',
};

const en: Dict = {
  'app.title': 'Cutting Edge v2',
  'app.subtitle': 'Sports video editor',
  'menu.file': 'File',
  'menu.edit': 'Edit',
  'menu.view': 'View',
  'menu.ai': 'AI',
  'menu.help': 'Help',
  'panel.media': 'Media',
  'panel.preview': 'Preview',
  'panel.properties': 'Properties',
  'panel.timeline': 'Timeline',
  'media.empty': 'No clips imported yet',
  'media.import': 'Import clips',
  'preview.empty': 'Start by importing 10 clips and one reference',
  'timeline.empty': 'Timeline is empty',
  'status.backend.online': 'Processing core connected',
  'status.backend.offline': 'Processing core unreachable',
  'status.offline.mode': 'Offline mode',
  'status.version': 'Version',
  'wizard.title': 'Style Match',
  'wizard.step.1': 'Reference intake',
  'wizard.step.2': 'DNA extraction',
  'wizard.step.3': 'Clip analysis',
  'wizard.step.4': 'Compatibility',
  'wizard.step.5': 'EDL build',
};

const dictionaries: Record<Language, Dict> = { fa, en };

/** Direction of a language, used for the document root and canvas text. */
export function directionOf(language: Language): Direction {
  return language === 'fa' ? 'rtl' : 'ltr';
}

/** Translate a key, falling back to the key itself (never throws in UI). */
export function translate(language: Language, key: string): string {
  return dictionaries[language][key] ?? key;
}

export const AVAILABLE_LANGUAGES: readonly Language[] = ['fa', 'en'];
