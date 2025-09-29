import gsap from "gsap";
import type { Attachment } from 'svelte/attachments';

export const slide: Attachment = (element) => {
    gsap.fromTo(element,
        { opacity: 0, y: 20 },
        { opacity: 1, y: 0, duration: 0.5, ease: "power2.out", delay: 0.2 }
    );
};

export const fade: Attachment = (element) => {
    gsap.fromTo(element,
        { opacity: 0 },
        { opacity: 1, duration: 0.5, ease: "power2.out", delay: 0.2 }
    );
}