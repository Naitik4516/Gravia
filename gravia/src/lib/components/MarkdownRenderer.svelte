<script lang="ts">
    import { renderMarkdown, hasMarkdownSyntax } from "$lib/chat/markdownService";
    import { onMount } from "svelte";
    import { toast } from "svelte-sonner";

    let {
        content = $bindable(""),
        enableMarkdown = $bindable(true),
        className = $bindable(""),
    }: {
        content: string;
        enableMarkdown: boolean;
        className: string;
    } = $props();

    let renderedContent = $derived(
        enableMarkdown && hasMarkdownSyntax(content)
            ? renderMarkdown(content)
            : content,
    );

    let isMarkdown = $derived(enableMarkdown && hasMarkdownSyntax(content));

    let markdownContainer = $state<HTMLDivElement>();
    onMount(() => {
        if (isMarkdown && markdownContainer) {
            addCodeBlockButtons();
        }
    });

    $effect(() => {
        if (isMarkdown && markdownContainer) {
            setTimeout(() => addCodeBlockButtons(), 0);
        }
    });

    function addCodeBlockButtons() {
        const codeBlocks = markdownContainer.querySelectorAll("pre:has(code)");

        codeBlocks.forEach((block, index) => {
            // Skip if buttons already added
            if (block.querySelector(".code-actions")) return;

            const code = block.querySelector("code");
            if (!code) return;

            const language = getLanguageFromCode(code);
            const codeText = code.textContent || "";
            // Create actions container
            const actionsDiv = document.createElement("div");
            actionsDiv.className = "code-actions";

            // Language label (left side)
            if (language) {
                const langLabel = document.createElement("span");
                langLabel.className = "language-label";
                langLabel.textContent = language;
                actionsDiv.appendChild(langLabel);
            }

            // Buttons container (right side)
            const buttonsContainer = document.createElement("div");
            buttonsContainer.className = "action-buttons";

            // Copy button
            const copyBtn = createActionButton("copy", "Copy", () =>
                copyToClipboard(codeText),
            );
            buttonsContainer.appendChild(copyBtn);

            // Wrap/Unwrap button
            const wrapBtn = createActionButton("wrap", "Wrap", () =>
                toggleWrap(block),
            );
            buttonsContainer.appendChild(wrapBtn);

            // Download button
            const downloadBtn = createActionButton("download", "Download", () =>
                downloadCode(codeText, language, index),
            );
            buttonsContainer.appendChild(downloadBtn);

            // Run button (for executable languages)
            if (isExecutableLanguage(language)) {
                const runBtn = createActionButton("run", "Run", () =>
                    runCode(codeText, language),
                );
                buttonsContainer.appendChild(runBtn);
            }

            actionsDiv.appendChild(buttonsContainer);

            block.style.position = "relative";
            block.appendChild(actionsDiv);
        });
    }

    function createActionButton(
        type: string,
        tooltip: string,
        onClick: () => void,
    ): HTMLButtonElement {
        const button = document.createElement("button");
        button.className = `action-btn action-btn-${type}`;
        button.title = tooltip;
        button.onclick = onClick;

        // Add icons
        const icons = {
            copy: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
				<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
			</svg>`,
            wrap: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<path d="M3 12h13l-3-3m0 6l3-3"></path>
				<path d="M3 17v4a2 2 0 0 0 2 2h4"></path>
			</svg>`,
            download: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
				<polyline points="7,10 12,15 17,10"></polyline>
				<line x1="12" y1="15" x2="12" y2="3"></line>
			</svg>`,
            run: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<polygon points="5,3 19,12 5,21"></polygon>
			</svg>`,
        };

        button.innerHTML = icons[type as keyof typeof icons] || "";
        return button;
    }

    function getLanguageFromCode(code: HTMLElement): string {
        const className = code.className;
        const match = className.match(/language-(\w+)/);
        return match ? match[1] : "";
    }

    function isExecutableLanguage(language: string): boolean {
        const executableLanguages = [
            "javascript",
            "js",
            "python",
            "py",
            "node",
            "bash",
            "sh",
        ];
        return executableLanguages.includes(language.toLowerCase());
    }
    async function copyToClipboard(text: string) {
        try {
            await navigator.clipboard.writeText(text);
            // Show visual feedback
            showCopyFeedback();
        } catch (err) {
            console.error("Failed to copy:", err);
            // Fallback for older browsers
            fallbackCopyToClipboard(text);
        }
    }

    function fallbackCopyToClipboard(text: string) {
        const textArea = document.createElement("textarea");
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        try {
            document.execCommand("copy");
            showCopyFeedback();
        } catch (err) {
            console.error("Fallback copy failed:", err);
        }
        document.body.removeChild(textArea);
    }

    function showCopyFeedback() {
        toast.success("Code copied to clipboard!");
    }
    function toggleWrap(block: Element) {
        const code = block.querySelector("code");
        if (!code) return;

        const pre = block as HTMLPreElement;
        const isWrapped =
            pre.style.whiteSpace === "pre-wrap" ||
            pre.classList.contains("wrapped");

        if (isWrapped) {
            // Unwrap
            pre.style.whiteSpace = "pre";
            pre.style.overflowX = "auto";
            code.style.whiteSpace = "pre";
            code.style.wordBreak = "normal";
            pre.classList.remove("wrapped");
        } else {
            // Wrap
            pre.style.whiteSpace = "pre-wrap";
            pre.style.overflowX = "visible";
            code.style.whiteSpace = "pre-wrap";
            code.style.wordBreak = "break-word";
            pre.classList.add("wrapped");
        }

        // Update button icon or state if needed
        const wrapBtn = block.querySelector(".action-btn-wrap");
        if (wrapBtn) {
            wrapBtn.title = isWrapped ? "Wrap" : "Unwrap";
        }
    }

    function downloadCode(text: string, language: string, index: number) {
        const extensions: { [key: string]: string } = {
            javascript: "js",
            js: "js",
            python: "py",
            py: "py",
            typescript: "ts",
            ts: "ts",
            html: "html",
            css: "css",
            json: "json",
            bash: "sh",
            sh: "sh",
        };

        const extension = extensions[language.toLowerCase()] || "txt";
        const filename = `code-block-${index + 1}.${extension}`;

        const blob = new Blob([text], { type: "text/plain" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
    }

    function runCode(text: string, language: string) {
        // This is a placeholder - in a real implementation, you'd want to:
        // 1. For JavaScript: use eval() or a sandboxed environment
        // 2. For Python: send to a backend service
        // 3. For other languages: integrate with appropriate runtime

        console.log(`Running ${language} code:`, text);
        alert(`Code execution not implemented yet for ${language}`);
    }
</script>

{#if isMarkdown}
    <div class="markdown-content {className}" bind:this={markdownContainer}>
        {@html renderedContent}
    </div>
{:else}
    <div class="text-content {className}">
        {content}
    </div>
{/if}

<style>
    :global(.markdown-content) {
        line-height: 1.6;
        text-align: left;
        color: inherit;
        word-wrap: break-word;
        overflow-wrap: break-word;
    }

    :global(.markdown-content h1),
    :global(.markdown-content h2),
    :global(.markdown-content h3),
    :global(.markdown-content h4),
    :global(.markdown-content h5),
    :global(.markdown-content h6) {
        margin-top: 1.5em;
        margin-bottom: 0.5em;
        font-weight: 600;
        text-align: left;
        color: inherit;
    }

    :global(.markdown-content h1) {
        font-size: 1.875rem;
    }
    :global(.markdown-content h2) {
        font-size: 1.5rem;
    }
    :global(.markdown-content h3) {
        font-size: 1.25rem;
    }
    :global(.markdown-content h4) {
        font-size: 1.125rem;
    }
    :global(.markdown-content h5) {
        font-size: 1rem;
    }
    :global(.markdown-content h6) {
        font-size: 0.875rem;
    }

    :global(.markdown-content p) {
        margin-bottom: 1em;
        text-align: left;
        color: inherit;
    }

    :global(.markdown-content ul),
    :global(.markdown-content ol) {
        margin-bottom: 1em;
        padding-left: 1.5em;
        text-align: left;
    }

    :global(.markdown-content li) {
        margin-bottom: 0.25em;
        text-align: left;
        color: inherit;
    }

    :global(.markdown-content blockquote) {
        margin: 1em 0;
        padding-left: 1em;
        border-left: 4px solid #6b7280;
        font-style: italic;
        color: #9ca3af;
        text-align: left;
    }
    :global(.markdown-content code) {
        background-color: #1a1a1a;
        color: #60a5fa;
        padding: 0.2rem 0.4rem;
        border-radius: 0.375rem;
        font-family: "Consolas", "Monaco", "Courier New", monospace;
        font-size: 0.875em;
        word-break: break-all;
        white-space: pre-wrap;
        overflow-wrap: break-word;
    }
    :global(.markdown-content pre) {
        background-color: #0a0a0a;
        color: #e5e7eb;
        padding: 3rem 1.25rem 1.25rem 1.25rem;
        border-radius: 0.75rem;
        overflow-x: auto;
        overflow-y: hidden;
        margin: 1em 0;
        max-width: 100%;
        width: 100%;
        text-align: left;
        box-shadow:
            0 8px 16px -4px rgba(0, 0, 0, 0.4),
            0 4px 8px -2px rgba(0, 0, 0, 0.2);
        scrollbar-width: thin;
        scrollbar-color: #333333 transparent;
        position: relative;
        white-space: pre;
        word-wrap: normal;
        word-break: normal;
    }

    :global(.markdown-content pre::-webkit-scrollbar) {
        height: 8px;
    }
    :global(.markdown-content pre::-webkit-scrollbar-track) {
        background: #1a1a1a;
        border-radius: 4px;
    }

    :global(.markdown-content pre::-webkit-scrollbar-thumb) {
        background-color: #333333;
        border-radius: 4px;
    }

    :global(.markdown-content pre::-webkit-scrollbar-thumb:hover) {
        background-color: #4a4a4a;
    }
    :global(.markdown-content pre code) {
        background-color: transparent;
        padding: 0;
        border-radius: 0;
        color: inherit;
        word-break: normal;
        white-space: pre;
        overflow-wrap: normal;
        font-family: "Consolas", "Monaco", "Courier New", monospace;
        line-height: 1.5;
        display: block;
        width: 100%;
    } /* Code Actions Buttons */
    :global(.code-actions) {
        position: absolute;
        top: 0.5rem;
        left: 0.5rem;
        right: 0.75rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        opacity: 1;
        z-index: 10;
        background-color: rgba(10, 10, 10, 0.95);
        padding: 0.5rem 0.75rem 0.5rem 0.5rem;
        border-radius: 0.5rem;
        height: 2rem;
    }
    :global(.action-buttons) {
        display: flex;
        align-items: center;
        gap: 0.375rem;
    }
    :global(.language-label) {
        background-color: transparent;
        color: #9ca3af;
        padding: 0.125rem 0.375rem 0.125rem 0.25rem;
        border-radius: 0.25rem;
        font-size: 0.75rem;
        font-family: "Consolas", "Monaco", "Courier New", monospace;
        text-transform: uppercase;
        font-weight: 500;
        letter-spacing: 0.05em;
    }
    :global(.action-btn) {
        background-color: transparent;
        color: #9ca3af;
        padding: 0.25rem;
        border-radius: 0.25rem;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.2s ease;
        width: 28px;
        height: 28px;
    }
    :global(.action-btn:hover) {
        background-color: #333333;
        color: #f9fafb;
        transform: translateY(-1px);
    }

    :global(.action-btn-copy:hover) {
        color: #10b981;
        border-color: #10b981;
    }

    :global(.action-btn-wrap:hover) {
        color: #3b82f6;
        border-color: #3b82f6;
    }

    :global(.action-btn-download:hover) {
        color: #8b5cf6;
        border-color: #8b5cf6;
    }

    :global(.action-btn-run:hover) {
        color: #f59e0b;
        border-color: #f59e0b;
    }
    :global(.action-btn svg) {
        width: 16px;
        height: 16px;
    }

    /* Copy feedback animations */
    :global {
        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }

        @keyframes slideOut {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(100%);
                opacity: 0;
            }
        }
    }

    :global(.markdown-content a) {
        color: #60a5fa;
        text-decoration: underline;
        word-break: break-word;
    }

    :global(.markdown-content a:hover) {
        color: #3b82f6;
    }

    :global(.markdown-content table) {
        width: 100%;
        border-collapse: collapse;
        margin: 1em 0;
        overflow-x: auto;
        display: block;
        white-space: nowrap;
    }

    :global(.markdown-content table thead),
    :global(.markdown-content table tbody),
    :global(.markdown-content table tr) {
        display: table;
        width: 100%;
        table-layout: fixed;
    }

    :global(.markdown-content th),
    :global(.markdown-content td) {
        border: 1px solid #4b5563;
        padding: 0.5rem;
        text-align: left;
        color: inherit;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    :global(.markdown-content th) {
        background-color: #374151;
        font-weight: 600;
        color: #f9fafb;
    }

    :global(.markdown-content hr) {
        margin: 2em 0;
        border: none;
        border-top: 1px solid #4b5563;
    }

    :global(.markdown-content img) {
        max-width: 100%;
        height: auto;
        border-radius: 0.5rem;
    }

    /* Subscript and Superscript styling */
    :global(.markdown-content sub) {
        vertical-align: sub;
        font-size: 0.75em;
        color: inherit;
    }

    :global(.markdown-content sup) {
        vertical-align: super;
        font-size: 0.75em;
        color: inherit;
    }
    /* Math (KaTeX) styling */
    :global(.markdown-content .katex) {
        font-size: 1em;
        color: #f9fafb !important;
        overflow-x: auto;
        max-width: 100%;
        scrollbar-width: thin;
        scrollbar-color: #4b5563 transparent;
    }

    :global(.markdown-content .katex::-webkit-scrollbar) {
        height: 4px;
    }

    :global(.markdown-content .katex::-webkit-scrollbar-track) {
        background: transparent;
    }

    :global(.markdown-content .katex::-webkit-scrollbar-thumb) {
        background-color: #4b5563;
        border-radius: 2px;
    }

    :global(.markdown-content .katex-display) {
        margin: 1em 0;
        text-align: center;
        overflow-x: auto;
        max-width: 100%;
        padding: 0.5rem 0;
    }

    :global(.markdown-content .katex-display > .katex) {
        display: inline-block;
        white-space: nowrap;
        max-width: 100%;
        overflow-x: auto;
        text-align: center;
    }

    /* Inline math should be inline */
    :global(.markdown-content .katex:not(.katex-display .katex)) {
        display: inline;
        white-space: nowrap;
        vertical-align: baseline;
    }

    /* Improve URL linkification styling */
    :global(.markdown-content a[href^="http"]) {
        color: #60a5fa;
        text-decoration: underline;
        word-break: break-all;
        overflow-wrap: break-word;
    }

    :global(.markdown-content a[href^="http"]:hover) {
        color: #3b82f6;
    }

    /* Text content fallback styling */
    :global(.text-content) {
        line-height: 1.6;
        text-align: left;
        color: inherit;
        word-wrap: break-word;
        overflow-wrap: break-word;
        white-space: pre-wrap;
    }

    /* Dark mode styles */
    :global(.dark .markdown-content blockquote) {
        border-left-color: #4b5563;
        color: #9ca3af;
    }
    :global(.dark .markdown-content code) {
        background-color: #1a1a1a;
        color: #60a5fa;
        border-color: #333333;
    }

    :global(.dark .markdown-content th),
    :global(.dark .markdown-content td) {
        border-color: #4b5563;
    }

    :global(.dark .markdown-content th) {
        background-color: #374151;
    }

    :global(.dark .markdown-content hr) {
        border-top-color: #4b5563;
    }

    /* Dark mode for math elements */
    :global(.dark .markdown-content .katex) {
        color: #f9fafb !important;
    }

    /* Dark mode for auto-linked URLs */
    :global(.dark .markdown-content a[href^="http"]) {
        color: #93c5fd;
    }

    :global(.dark .markdown-content a[href^="http"]:hover) {
        color: #60a5fa;
    }
    /* Mobile responsiveness */
    @media (max-width: 768px) {
        :global(.markdown-content) {
            font-size: 0.9rem;
        }

        :global(.markdown-content table) {
            font-size: 0.8rem;
        }

        :global(.markdown-content .katex) {
            font-size: 0.9em;
        }
        :global(.markdown-content pre) {
            padding: 2.5rem 0.75rem 0.75rem 0.75rem;
            font-size: 0.8rem;
            overflow-x: auto;
            max-width: calc(100vw - 2rem);
        }
        :global(.code-actions) {
            opacity: 1;
            position: absolute;
            top: 0.25rem;
            left: 0.375rem;
            right: 0.5rem;
            background-color: rgba(10, 10, 10, 0.95);
            padding: 0.375rem 0.5rem 0.375rem 0.375rem;
            border-radius: 0.375rem;
            height: 1.75rem;
        }

        :global(.language-label) {
            font-size: 0.7rem;
            padding: 0.2rem 0.4rem 0.2rem 0.25rem;
        }
        :global(.action-btn) {
            width: 26px;
            height: 26px;
            padding: 0.2rem;
        }
    }
</style>
