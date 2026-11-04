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
  'menu.theme': 'تم',
  'menu.language': 'زبان',
  'panel.media': 'رسانه',
  'panel.preview': 'پیش‌نمایش',
  'panel.properties': 'خصوصیات',
  'panel.timeline': 'تایم‌لاین',
  'media.empty': 'هنوز کلیپی وارد نشده است',
  'media.empty.hint': 'فایل‌ها را اینجا رها کنید یا دکمهٔ ورود را بزنید',
  'media.import': 'ورود کلیپ',
  'media.remove': 'حذف',
  'media.count': 'کلیپ',
  'media.error.extension': 'فرمت پشتیبانی نمی‌شود',
  'media.error.duplicate': 'این فایل قبلاً اضافه شده است',
  'media.reference': 'مرجع',
  'media.source': 'منبع',
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
  'wizard.next': 'گام بعدی',
  'wizard.back': 'بازگشت',
  'wizard.start': 'شروع تحلیل',
  'wizard.progress': 'پیشرفت ویزارد',
  'wizard.needs.reference': 'یک ویدیوی مرجع انتخاب کنید',
  'wizard.needs.clips': 'حداقل یک کلیپ منبع لازم است',
  'wizard.reference.selected': 'رفرنس انتخاب‌شده',
  'wizard.no.reference': 'رفرنسی انتخاب نشده',
  'wizard.independence': 'تحلیل محلی، بدون ارسال به اینترنت',
  'palette.placeholder': 'دستور را جست‌وجو کنید…',
  'palette.label': 'پالت دستورها',
  'palette.action.theme': 'تغییر تم',
  'palette.action.language': 'تغییر زبان',
  'palette.action.import': 'ورود کلیپ',
  'palette.action.wizard': 'رفتن به ویزارد سبک',
  'common.close': 'بستن',
  'common.loading': 'در حال پردازش…',
  'common.cancel': 'انصراف',
  'a11y.skip': 'پرش به محتوای اصلی',
};

const en: Dict = {
  'app.title': 'Cutting Edge v2',
  'app.subtitle': 'Sports video editor',
  'menu.file': 'File',
  'menu.edit': 'Edit',
  'menu.view': 'View',
  'menu.ai': 'AI',
  'menu.help': 'Help',
  'menu.theme': 'Theme',
  'menu.language': 'Language',
  'panel.media': 'Media',
  'panel.preview': 'Preview',
  'panel.properties': 'Properties',
  'panel.timeline': 'Timeline',
  'media.empty': 'No clips imported yet',
  'media.empty.hint': 'Drop files here or use the import button',
  'media.import': 'Import clips',
  'media.remove': 'Remove',
  'media.count': 'clips',
  'media.error.extension': 'Unsupported format',
  'media.error.duplicate': 'This file is already imported',
  'media.reference': 'Reference',
  'media.source': 'Source',
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
  'wizard.next': 'Next step',
  'wizard.back': 'Back',
  'wizard.start': 'Start analysis',
  'wizard.progress': 'Wizard progress',
  'wizard.needs.reference': 'Select one reference video',
  'wizard.needs.clips': 'At least one source clip is required',
  'wizard.reference.selected': 'Selected reference',
  'wizard.no.reference': 'No reference selected',
  'wizard.independence': 'Analysed locally — nothing leaves this machine',
  'palette.placeholder': 'Search a command…',
  'palette.label': 'Command palette',
  'palette.action.theme': 'Switch theme',
  'palette.action.language': 'Switch language',
  'palette.action.import': 'Import clips',
  'palette.action.wizard': 'Go to Style Match wizard',
  'common.close': 'Close',
  'common.loading': 'Working…',
  'common.cancel': 'Cancel',
  'a11y.skip': 'Skip to main content',
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

/** All keys of a language — used by the completeness test. */
export function keysOf(language: Language): string[] {
  return Object.keys(dictionaries[language]);
}

export const AVAILABLE_LANGUAGES: readonly Language[] = ['fa', 'en'];
