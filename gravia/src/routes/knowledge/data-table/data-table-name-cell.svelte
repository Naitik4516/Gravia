<script lang="ts">
    import type { KnowledgeItem } from '$lib/knowledge/types';
    
    let {
        item,
        onEdit
    }: {
        item: KnowledgeItem;
        onEdit: (item: KnowledgeItem) => void;
    } = $props();
</script>

<button 
    class="font-medium truncate max-w-[240px] text-left hover:text-primary transition-colors cursor-pointer bg-transparent border-none p-0" 
    title={item.name}
    onclick={() => onEdit(item)}
>
    {item.name}
</button>