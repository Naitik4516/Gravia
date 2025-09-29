// Type declarations for markdown-it plugins without official types

declare module 'markdown-it-sub' {
  import { PluginSimple } from 'markdown-it';
  const sub: PluginSimple;
  export = sub;
}

declare module 'markdown-it-sup' {
  import { PluginSimple } from 'markdown-it';
  const sup: PluginSimple;
  export = sup;
}

declare module 'markdown-it-katex' {
  import { PluginWithOptions } from 'markdown-it';
  
  interface KatexOptions {
    throwOnError?: boolean;
    errorColor?: string;
    strict?: boolean;
    macros?: Record<string, string>;
    fleqn?: boolean;
    leqno?: boolean;
    minRuleThickness?: number;
    colorIsTextColor?: boolean;
    output?: 'html' | 'mathml' | 'htmlAndMathml';
    trust?: boolean;
    globalGroup?: boolean;
  }
  
  const katex: PluginWithOptions<KatexOptions>;
  export = katex;
}
