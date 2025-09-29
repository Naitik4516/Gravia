import MarkdownIt from 'markdown-it';
import DOMPurify from 'dompurify';
import hljs from 'markdown-it-highlightjs';
import anchor from 'markdown-it-anchor';
import sub from 'markdown-it-sub';
import sup from 'markdown-it-sup';
import katex from 'markdown-it-katex';
import 'highlight.js/styles/github-dark.css';
import 'katex/dist/katex.min.css';

// Configure markdown-it with plugins
const md = new MarkdownIt({
	html: true,
	linkify: true,
	typographer: true,
	breaks: false  // Disable automatic line breaks to prevent issues in code blocks
})
	.use(hljs, {
		auto: true,
		code: true
	})
	.use(anchor, {
		permalink: false,
		permalinkBefore: true,
		permalinkSymbol: '#'
	})
	.use(sub)
	.use(sup)
	.use(katex, {
		throwOnError: false,
		errorColor: '#cc0000'
	});


/**
 * Converts markdown text to sanitized HTML
 * @param markdown - The markdown text to render
 * @returns Sanitized HTML string
 */
export function renderMarkdown(markdown: string): string {
	if (!markdown) return '';
	
	// Convert markdown to HTML
	const html = md.render(markdown);
	// Sanitize the HTML to prevent XSS attacks
	const sanitizedHtml = DOMPurify.sanitize(html, {
		ALLOWED_TAGS: [
			'p', 'br', 'strong', 'em', 'u', 's', 'del', 'ins',
			'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
			'ul', 'ol', 'li',
			'blockquote',
			'code', 'pre',
			'a',
			'img',
			'table', 'thead', 'tbody', 'tr', 'th', 'td',
			'hr',
			'span', 'div',
			'sub', 'sup',  // subscript and superscript
			'math', 'semantics', 'mrow', 'msup', 'msub', 'mfrac', 'msqrt', 'mroot',
			'mi', 'mn', 'mo', 'mtext', 'mspace', 'munder', 'mover', 'munderover',
			'mtable', 'mtr', 'mtd', 'mlabeledtr', 'maligngroup', 'malignmark',
			'annotation', 'annotation-xml'
		],
		ALLOWED_ATTR: [
			'href', 'title', 'alt', 'src', 'width', 'height',
			'class', 'id',
			'target', 'rel',
			// Math-related attributes
			'mathvariant', 'mathsize', 'mathcolor', 'mathbackground',
			'displaystyle', 'scriptlevel', 'data-*',
			'style', // Allow style for KaTeX rendering
			'role', 'aria-hidden', 'focusable' // Accessibility attributes
		],
		ALLOWED_URI_REGEXP: /^(?:(?:(?:f|ht)tps?|mailto|tel|callto|cid|xmpp):|[^a-z]|[a-z+.\-]+(?:[^a-z+.\-:]|$))/i
	});

	// Ensure all links open in a new tab and are safe
	return sanitizedHtml.replace(
		/<a\s/gi,
		'<a target="_blank" rel="noopener noreferrer" '
	);
}

/**
 * Checks if a string contains markdown syntax
 * @param text - The text to check
 * @returns true if the text appears to contain markdown
 */
export function hasMarkdownSyntax(text: string): boolean {
	if (!text) return false;
	
	// Simple regex patterns to detect common markdown syntax
	const markdownPatterns = [
		/\*\*.*?\*\*/,      // Bold
		/\*.*?\*/,          // Italic
		/`.*?`/,            // Inline code
		/```[\s\S]*?```/,   // Code blocks
		/^#{1,6}\s/m,       // Headers
		/^\s*[-*+]\s/m,     // Unordered lists
		/^\s*\d+\.\s/m,     // Ordered lists
		/^\s*>/m,           // Blockquotes
		/\[.*?\]\(.*?\)/,   // Links
		/!\[.*?\]\(.*?\)/,  // Images
		/~.*?~/,            // Subscript
		/\^.*?\^/,          // Superscript
		/\$\$[\s\S]*?\$\$/, // Block math (LaTeX)
		/\$[^$\s].*?[^$\s]\$/, // Inline math (LaTeX) - improved pattern
		/https?:\/\/\S+/,   // URLs (for linkify detection)
		/www\.\S+/,         // www URLs (for linkify detection)
		/^\s*\|.*\|/m,      // Tables
		/---+/,             // Horizontal rules
		/~~.*?~~/           // Strikethrough
	];
	
	return markdownPatterns.some(pattern => pattern.test(text));
}
