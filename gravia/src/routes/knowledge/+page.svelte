<script lang="ts">
  import type { PageData } from "./$types";
  import type { KnowledgeItem } from "$lib/knowledge/types";
  import {
    type ColumnDef,
    type PaginationState,
    type SortingState,
    type ColumnFiltersState,
    type VisibilityState,
    type RowSelectionState,
    getCoreRowModel,
    getPaginationRowModel,
    getSortedRowModel,
    getFilteredRowModel,
  } from "@tanstack/table-core";
  import { createRawSnippet } from "svelte";
  import {
    createSvelteTable,
    FlexRender,
    renderComponent,
    renderSnippet,
  } from "$lib/components/ui/data-table/index.js";
  import * as Table from "$lib/components/ui/table/index.js";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Input } from "$lib/components/ui/input/index.js";
  import * as DropdownMenu from "$lib/components/ui/dropdown-menu/index.js";
  import * as Dialog from "$lib/components/ui/dialog/index.js";
  import { Label } from "$lib/components/ui/label/index.js";
  import { Textarea } from "$lib/components/ui/textarea/index.js";
  import DataTableCheckbox from "./data-table/data-table-checkbox.svelte";
  import DataTableSortButton from "./data-table/data-table-sort-button.svelte";
  import DataTableNameCell from "./data-table/data-table-name-cell.svelte";
  import { KnowledgeService } from "$lib/knowledge/knowledgeService";
  import { invalidateAll } from "$app/navigation";
  import * as Select from "$lib/components/ui/select/index.js";
  import { open } from '@tauri-apps/plugin-dialog';

  let { data }: { data: PageData } = $props();
  const items = (data.items || []) as KnowledgeItem[];

  // Modal states
  let showAddModal = $state(false);
  let showEditModal = $state(false);
  let editingItem = $state<KnowledgeItem | null>(null);

  // Loading states
  let isLoading = $state(false);
  let isSubmitting = $state(false);
  let error = $state<string | null>(null);

  // Form states
  let formData = $state({
    sourceType: "",
    file: null as string | null, // Changed to store file path instead of File object
    url: "",
    text: "",
    name: "",
    description: "",
    tag: "",
    chunkingMethod: "", // Add chunking method
  });

  // Source type options
  const sourceTypes = [
    { value: "file", label: "File" },
    { value: "url", label: "URL" },
    { value: "text", label: "Text" },
  ];

  // Chunking method options
  const chunkingMethods = [
    { 
      value: "document", 
      label: "Document", 
      description: "Fastest and cheapest method. Best for long and structured documents like PDFs, articles, and reports."
    },
    { 
      value: "semantic", 
      label: "Semantic", 
      description: "More intelligent chunking based on meaning and context. Better for complex or unstructured content."
    },
  ];

  // Delete confirmation dialogs
  let showDeleteAllDialog = $state(false);
  let showDeleteSelectedDialog = $state(false);

  function openAddModal() {
    formData = {
      sourceType: "",
      file: null,
      url: "",
      text: "",
      name: "",
      description: "",
      tag: "",
      chunkingMethod: "",
    };
    showAddModal = true;
  }

  async function handleFileSelect() {
    try {
      const selected = await open({
        multiple: false,
        directory: false,
        filters: [
          {
            name: 'Documents',
            extensions: ['txt', 'pdf', 'doc', 'docx', 'md', 'json', 'csv']
          }
        ]
      });
      
      if (selected) {
        formData.file = selected as string;
      }
    } catch (err) {
      console.error('Error selecting file:', err);
      error = 'Failed to select file';
    }
  }

  function openEditModal(item: KnowledgeItem) {
    editingItem = item;
    formData = {
      sourceType: "", // Not editable
      file: null, // Not editable
      url: "", // Not editable
      text: "", // Not editable
      chunkingMethod: "", // Not editable
      name: item.name,
      description: item.description,
      tag: item.metadata?.tag || item.metadata?.user_tag || "",
    };
    showEditModal = true;
  }

  async function handleAddSubmit() {
    if (isSubmitting) return;

    try {
      isSubmitting = true;
      error = null;

      await KnowledgeService.createKnowledge({
        name: formData.name,
        description: formData.description || undefined,
        tag: formData.tag || undefined,
        source_type: formData.sourceType as "file" | "url" | "text",
        chunking_method: formData.chunkingMethod as "document" | "semantic" || undefined,
        path: formData.file || undefined, // Send file path directly
        url: formData.url || undefined,
        text: formData.text || undefined,
      });

      showAddModal = false;
      // Refresh the page data
      await invalidateAll();
    } catch (err) {
      error =
        err instanceof Error ? err.message : "Failed to create knowledge item";
      console.error("Error creating knowledge:", err);
    } finally {
      isSubmitting = false;
    }
  }

  async function handleEditSubmit() {
    if (isSubmitting || !editingItem) return;

    try {
      isSubmitting = true;
      error = null;

      await KnowledgeService.updateKnowledge(editingItem.id, {
        name: formData.name || undefined,
        description: formData.description || undefined,
        tag: formData.tag || undefined,
      });

      showEditModal = false;
      editingItem = null;
      // Refresh the page data
      await invalidateAll();
    } catch (err) {
      error =
        err instanceof Error ? err.message : "Failed to update knowledge item";
      console.error("Error updating knowledge:", err);
    } finally {
      isSubmitting = false;
    }
  }

  function handleDeleteSelected() {
    const selectedCount = Object.keys(rowSelection).length;
    if (selectedCount > 0) {
      showDeleteSelectedDialog = true;
    }
  }

  function handleDeleteAll() {
    showDeleteAllDialog = true;
  }

  async function confirmDeleteSelected() {
    if (isSubmitting) return;

    try {
      isSubmitting = true;
      error = null;

      // Now rowSelection contains actual item IDs as keys
      const selectedIds = Object.keys(rowSelection);
      await KnowledgeService.deleteMultipleKnowledge(selectedIds);

      rowSelection = {};
      showDeleteSelectedDialog = false;
      // Refresh the page data
      await invalidateAll();
    } catch (err) {
      error =
        err instanceof Error ? err.message : "Failed to delete selected items";
      console.error("Error deleting selected items:", err);
    } finally {
      isSubmitting = false;
    }
  }

  async function confirmDeleteAll() {
    if (isSubmitting) return;

    try {
      isSubmitting = true;
      error = null;

      await KnowledgeService.deleteAllKnowledge();

      rowSelection = {};
      showDeleteAllDialog = false;
      // Refresh the page data
      await invalidateAll();
    } catch (err) {
      error = err instanceof Error ? err.message : "Failed to delete all items";
      console.error("Error deleting all items:", err);
    } finally {
      isSubmitting = false;
    }
  }

  function formatSize(bytes: number) {
    if (bytes < 1024) return bytes + " B";
    const units = ["KB", "MB", "GB"];
    let v = bytes / 1024;
    let i = 0;
    while (v >= 1024 && i < units.length - 1) {
      v /= 1024;
      i++;
    }
    return v.toFixed(1) + " " + units[i];
  }

  // custom snippets for cells
  const descSnippet = createRawSnippet<[string]>((getVal) => {
    const val = getVal();
    return {
      render: () =>
        `<div class=\"truncate max-w-[390px] text-neutral-300 text-xs\" title=\"${val}\">${val}</div>`,
    };
  });

  const tagSnippet = createRawSnippet<[string]>((getVal) => {
    const val = getVal();
    return {
      render: () =>
        `<span class=\"inline-flex items-center rounded bg-primary/15 px-2 py-0.5 text-[10px] uppercase tracking-wide text-primary ring-1 ring-inset ring-primary/30\">${val}</span>`,
    };
  });

  const sizeSnippet = createRawSnippet<[string]>((getVal) => {
    const val = getVal();
    return { render: () => `<div class=\"tabular-nums\">${val}</div>` };
  });

  const dateSnippet = createRawSnippet<[string]>((getVal) => {
    const val = getVal();
    return { render: () => `<time>${val}</time>` };
  });

  const statusSnippet = createRawSnippet<[string]>((getVal) => {
    const val = getVal();
    const statusColors: Record<string, string> = {
      'completed': 'bg-green-700/20 text-green-400 ring-green-600/20',
      'processing': 'bg-yellow-700/20 text-yellow-400 ring-yellow-600/20',
      'failed': 'bg-red-700/20 text-red-400 ring-red-600/20',
      'pending': 'bg-gray-700/20 text-gray-400 ring-gray-600/20'
    };
    const colorClass = statusColors[val.toLowerCase()] || statusColors['pending'];
    return {
      render: () =>
        `<span class="inline-flex items-center rounded-md px-2 py-1 text-[10px] font-medium uppercase tracking-wide ring-1 ring-inset ${colorClass}">${val}</span>`,
    };
  });

  const columns: ColumnDef<KnowledgeItem>[] = [
    {
      id: "select",
      header: ({ table }) =>
        renderComponent(DataTableCheckbox, {
          checked: table.getIsAllPageRowsSelected(),
          indeterminate:
            table.getIsSomePageRowsSelected() &&
            !table.getIsAllPageRowsSelected(),
          onCheckedChange: (v: boolean) => table.toggleAllPageRowsSelected(!!v),
          "aria-label": "Select all",
        }),
      cell: ({ row }) =>
        renderComponent(DataTableCheckbox, {
          checked: row.getIsSelected(),
          onCheckedChange: (v: boolean) => row.toggleSelected(!!v),
          "aria-label": "Select row",
        }),
      enableSorting: false,
      enableHiding: false,
    },
    {
      accessorKey: "name",
      header: ({ column }) => {
        const nameHeaderSnippet = createRawSnippet(() => {
          return { render: () => `Name` };
        });
        return renderComponent(DataTableSortButton, {
          onclick: () => column.toggleSorting(column.getIsSorted() === "asc"),
          sortDirection: column.getIsSorted(),
          children: nameHeaderSnippet,
        });
      },
      cell: ({ row }) =>
        renderComponent(DataTableNameCell, {
          item: row.original,
          onEdit: openEditModal,
        }),
      filterFn: (row, _columnId, value: string) => {
        const v = String(row.getValue("name")).toLowerCase();
        const full = [
          row.original.description,
          row.original.metadata?.tag || row.original.metadata?.user_tag,
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        const q = (value || "").toLowerCase();
        return v.includes(q) || full.includes(q);
      },
    },
    {
      accessorKey: "file_type",
      header: ({ column }) => {
        const fileTypeHeaderSnippet = createRawSnippet(() => {
          return { render: () => `File Type` };
        });
        return renderComponent(DataTableSortButton, {
          onclick: () => column.toggleSorting(column.getIsSorted() === "asc"),
          sortDirection: column.getIsSorted(),
          children: fileTypeHeaderSnippet,
        });
      },
      cell: ({ row }) => row.getValue("file_type"),
    },
    {
      accessorKey: "status",
      header: ({ column }) => {
        const statusHeaderSnippet = createRawSnippet(() => {
          return { render: () => `Status` };
        });
        return renderComponent(DataTableSortButton, {
          onclick: () => column.toggleSorting(column.getIsSorted() === "asc"),
          sortDirection: column.getIsSorted(),
          children: statusHeaderSnippet,
        });
      },
      cell: ({ row }) => {
        const status = row.original.status || 'pending';
        return renderSnippet(statusSnippet, status);
      },
    },
    {
      accessorKey: "description",
      header: "Description",
      cell: ({ row }) =>
        renderSnippet(descSnippet, row.getValue("description")),
      enableSorting: false,
    },
    {
      accessorKey: "updated_at",
      header: ({ column }) => {
        const updatedHeaderSnippet = createRawSnippet(() => {
          return { render: () => `Updated` };
        });
        return renderComponent(DataTableSortButton, {
          onclick: () => column.toggleSorting(column.getIsSorted() === "asc"),
          sortDirection: column.getIsSorted(),
          children: updatedHeaderSnippet,
        });
      },
      cell: ({ row }) => {
        const date = new Date(
          row.original.updated_at * 1000,
        ).toLocaleDateString(undefined, {
          day: "2-digit",
          month: "short",
          year: "numeric",
        });
        return renderSnippet(dateSnippet, date);
      },
    },
    {
      id: "tag",
      header: "Tag",
      cell: ({ row }) => {
        const tag =
          row.original.metadata?.tag || row.original.metadata?.user_tag || "";
        return renderSnippet(tagSnippet, tag);
      },
      enableSorting: false,
    },
    {
      accessorKey: "size",
      header: ({ column }) => {
        const sizeHeaderSnippet = createRawSnippet(() => {
          return { render: () => `Size` };
        });
        return renderComponent(DataTableSortButton, {
          onclick: () => column.toggleSorting(column.getIsSorted() === "asc"),
          sortDirection: column.getIsSorted(),
          children: sizeHeaderSnippet,
        });
      },
      cell: ({ row }) => {
        const size = row.original.size;
        if (!size) return renderSnippet(sizeSnippet, "-");
        return renderSnippet(sizeSnippet, formatSize(size));
      },
    },
  ];

  // Table state
  let pagination = $state<PaginationState>({ pageIndex: 0, pageSize: 20 });
  let sorting = $state<SortingState>([]);
  let columnFilters = $state<ColumnFiltersState>([]);
  let columnVisibility = $state<VisibilityState>({});
  let rowSelection = $state<RowSelectionState>({});

  const table = createSvelteTable({
    get data() {
      return items;
    },
    columns,
    getRowId: (row) => row.id,
    state: {
      get pagination() {
        return pagination;
      },
      get sorting() {
        return sorting;
      },
      get columnFilters() {
        return columnFilters;
      },
      get columnVisibility() {
        return columnVisibility;
      },
      get rowSelection() {
        return rowSelection;
      },
    },
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    onPaginationChange: (u) => {
      pagination = typeof u === "function" ? u(pagination) : u;
    },
    onSortingChange: (u) => {
      sorting = typeof u === "function" ? u(sorting) : u;
    },
    onColumnFiltersChange: (u) => {
      columnFilters = typeof u === "function" ? u(columnFilters) : u;
    },
    onColumnVisibilityChange: (u) => {
      columnVisibility = typeof u === "function" ? u(columnVisibility) : u;
    },
    onRowSelectionChange: (u) => {
      rowSelection = typeof u === "function" ? u(rowSelection) : u;
    },
  });
</script>

<section class="p-6 h-screen flex flex-col justify-around">
  <header class="flex-shrink-0 space-y-4">
    <h1 class="text-5xl font-black tracking-tight text-center mb-10">Knowledge</h1>

    <!-- Controls under title -->
    <div class="flex gap-3 sm:items-center justify-between">
      <div class="flex gap-2 items-center w-full">
        <Input
          placeholder="Search..."
          value={(table.getColumn("name")?.getFilterValue() as string) ?? ""}
          oninput={(e: any) =>
            table.getColumn("name")?.setFilterValue(e.currentTarget.value)}
          class="max-w-2/5 rounded-full px-2"
        />
        <Button
          variant="default"
          onclick={openAddModal}
          size="xl"
          aria-label="Add knowledge item">Add</Button
        >
        {#if Object.keys(rowSelection).length > 0}
          <Button
            variant="destructive"
            size="xl"
            onclick={handleDeleteSelected}
          >
            Delete Selected ({Object.keys(rowSelection).length})
          </Button>
        {/if}
        <Button variant="destructive" size="xl" onclick={handleDeleteAll}
          >Delete All</Button
        >
      </div>
      <DropdownMenu.Root>
        <DropdownMenu.Trigger>
          {#snippet child({ props })}
            <Button {...props} variant="outline" class="h-10">Columns</Button>
          {/snippet}
        </DropdownMenu.Trigger>
        <DropdownMenu.Content align="end">
          {#each table
            .getAllColumns()
            .filter((c) => c.getCanHide()) as column (column.id)}
            <DropdownMenu.CheckboxItem
              class="capitalize"
              bind:checked={
                () => column.getIsVisible(), (v) => column.toggleVisibility(!!v)
              }>{column.id}</DropdownMenu.CheckboxItem
            >
          {/each}
        </DropdownMenu.Content>
      </DropdownMenu.Root>
    </div>
  </header>

  <!-- Table container at bottom with fixed height -->
  <div class="flex-1 mt-6 min-h-0 ">
    <div
      class="h-full rounded-xl border border-neutral-800 bg-neutral-900/40 backdrop-blur flex flex-col"
    >
      <div class="flex-1 overflow-auto">
        <Table.Root>
          <Table.Header class="sticky top-0 bg-gray-900/70 backdrop-blur">
            {#each table.getHeaderGroups() as headerGroup (headerGroup.id)}
              <Table.Row>
                {#each headerGroup.headers as header (header.id)}
                  <Table.Head class="[&:has([role=checkbox])]:pl-3">
                    {#if !header.isPlaceholder}
                      <FlexRender
                        content={header.column.columnDef.header}
                        context={header.getContext()}
                      />
                    {/if}
                  </Table.Head>
                {/each}
              </Table.Row>
            {/each}
          </Table.Header>
          <Table.Body>
            {#each table.getRowModel().rows as row (row.id)}
              <Table.Row
                data-state={row.getIsSelected() && "selected"}
                class="cursor-pointer h-14 hover:bg-slate-900/50 transition-colors rounded"
                onclick={(e: MouseEvent) => {
                  // Only open edit modal if clicked outside of checkbox
                  const target = e.target as HTMLElement;
                  if (!target?.closest('[role="checkbox"]')) {
                    openEditModal(row.original);
                  }
                }}
              >
                {#each row.getVisibleCells() as cell (cell.id)}
                  <Table.Cell class="[&:has([role=checkbox])]:pl-3">
                    <FlexRender
                      content={cell.column.columnDef.cell}
                      context={cell.getContext()}
                    />
                  </Table.Cell>
                {/each}
              </Table.Row>
            {:else}
              <Table.Row>
                <Table.Cell colspan={columns.length} class="h-24 text-center"
                  >No results.</Table.Cell
                >
              </Table.Row>
            {/each}
          </Table.Body>
        </Table.Root>
      </div>
      <div
        class="flex-shrink-0 flex items-center justify-between px-4 py-3 gap-4 text-xs text-neutral-400 border-t border-gray-800"
      >
        <div class="text-muted-foreground flex-1 text-sm">
          {table.getFilteredSelectedRowModel().rows.length} of {table.getFilteredRowModel()
            .rows.length} selected.
        </div>
        <div class="space-x-2 flex items-center">
          <Button
            variant="outline"
            size="sm"
            onclick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}>Previous</Button
          >
          <span class="text-xs tabular-nums"
            >Page {table.getState().pagination.pageIndex + 1}</span
          >
          <Button
            variant="outline"
            size="sm"
            onclick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}>Next</Button
          >
        </div>
      </div>
    </div>
  </div>
</section>

<!-- Delete Selected Confirmation Dialog -->
<Dialog.Root bind:open={showDeleteSelectedDialog}>
  <Dialog.Content>
    <Dialog.Header>
      <Dialog.Title>Delete Selected Items</Dialog.Title>
      <Dialog.Description>
        Are you sure you want to delete {Object.keys(rowSelection).length} selected
        item{Object.keys(rowSelection).length === 1 ? "" : "s"}? This action
        cannot be undone.
      </Dialog.Description>
    </Dialog.Header>
    <Dialog.Footer>
      <Button
        variant="outline"
        onclick={() => (showDeleteSelectedDialog = false)}
        disabled={isLoading}>Cancel</Button
      >
      <Button
        variant="destructive"
        onclick={confirmDeleteSelected}
        disabled={isLoading}
      >
        {#if isLoading}
          <svg
            class="animate-spin -ml-1 mr-3 h-4 w-4 text-current"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              class="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              stroke-width="4"
            ></circle>
            <path
              class="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            ></path>
          </svg>
          Deleting...
        {:else}
          Delete
        {/if}
      </Button>
    </Dialog.Footer>
  </Dialog.Content>
</Dialog.Root>

<!-- Delete All Confirmation Dialog -->
<Dialog.Root bind:open={showDeleteAllDialog}>
  <Dialog.Content>
    <Dialog.Header>
      <Dialog.Title>Delete All Items</Dialog.Title>
      <Dialog.Description>
        Are you sure you want to delete all {items.length} knowledge items? This
        action cannot be undone.
      </Dialog.Description>
    </Dialog.Header>
    <Dialog.Footer>
      <Button
        variant="outline"
        onclick={() => (showDeleteAllDialog = false)}
        disabled={isLoading}>Cancel</Button
      >
      <Button
        variant="destructive"
        onclick={confirmDeleteAll}
        disabled={isLoading}
      >
        {#if isLoading}
          <svg
            class="animate-spin -ml-1 mr-3 h-4 w-4 text-current"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              class="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              stroke-width="4"
            ></circle>
            <path
              class="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            ></path>
          </svg>
          Deleting...
        {:else}
          Delete All
        {/if}
      </Button>
    </Dialog.Footer>
  </Dialog.Content>
</Dialog.Root>

<!-- Add Knowledge Modal -->
<Dialog.Root bind:open={showAddModal}>
  <Dialog.Content class="max-w-lg">
    <Dialog.Header>
      <Dialog.Title class="text-2xl font-semibold">Add Knowledge</Dialog.Title>
      <Dialog.Description class="text-sm text-muted-foreground">
        Add a new knowledge item to your collection.
      </Dialog.Description>
    </Dialog.Header>

    {#if error}
      <div
        class="bg-destructive/10 border border-destructive/20 text-destructive px-3 py-2 rounded-md text-sm"
      >
        {error}
      </div>
    {/if}

    <div class="space-y-6 py-4">
      <div class="flex justify-between space-y-2">
        <Label for="sourceType" class="text-sm font-medium">Source Type</Label>
        <Select.Root
          type="single"
          name="sourceType"
          bind:value={formData.sourceType}
        >
          <Select.Trigger class="w-[180px]">
            {formData.sourceType
              ? sourceTypes.find((t) => t.value === formData.sourceType)?.label
              : "Select source type"}
          </Select.Trigger>
          <Select.Content>
            <Select.Group>
              <Select.Label>Source Types</Select.Label>
              {#each sourceTypes as type}
                <Select.Item
                  value={type.value}
                  label={type.label}
                  disabled={type.value === "grapes"}
                >
                  {type.label}
                </Select.Item>
              {/each}
            </Select.Group>
          </Select.Content>
        </Select.Root>
      </div>

      <!-- Dynamic Source Field -->
      {#if formData.sourceType === "file"}
        <div class="space-y-2">
          <Label for="fileInput" class="text-sm font-medium">Select File</Label>
          <div class="space-y-3">
            <Button
              type="button"
              variant="outline"
              onclick={handleFileSelect}
              class="w-full justify-start text-left font-normal"
            >
              <svg class="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
              </svg>
              {formData.file ? 'Change File' : 'Choose File'}
            </Button>
            
            {#if formData.file}
              <div class="flex items-center gap-2 p-3 border rounded-md bg-green-50 border-green-200 dark:bg-green-950 dark:border-green-800">
                <div class="w-2 h-2 bg-green-500 rounded-full"></div>
                <span class="text-sm text-green-700 dark:text-green-300 font-medium">
                  Selected: {formData.file.split('\\').pop() || formData.file.split('/').pop()}
                </span>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onclick={() => formData.file = null}
                  class="ml-auto h-6 w-6 p-0 text-green-600 hover:text-green-800 dark:text-green-400"
                >
                  <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </Button>
              </div>
            {:else}
              <p class="text-xs text-muted-foreground">
                Supported formats: TXT, PDF, DOC, DOCX, MD, JSON, CSV
              </p>
            {/if}
          </div>
        </div>
      {:else if formData.sourceType === "url"}
        <div class="space-y-2">
          <Label for="urlInput" class="text-sm font-medium">URL</Label>
          <Input
            id="urlInput"
            type="url"
            bind:value={formData.url}
            placeholder="https://example.com/article"
            class="font-mono text-sm"
          />
          <p class="text-xs text-muted-foreground">
            Enter a web URL to extract and store its content
          </p>
        </div>
      {:else if formData.sourceType === "text"}
        <div class="space-y-2">
          <Label for="textInput" class="text-sm font-medium">Text Content</Label
          >
          <Textarea
            id="textInput"
            bind:value={formData.text}
            placeholder="Enter or paste your text content here..."
            class="min-h-[120px] resize-y"
          />
          <p class="text-xs text-muted-foreground">
            Paste any text content you want to store and search
          </p>
        </div>
      {:else if formData.sourceType === ""}
        <div
          class="rounded-lg border-2 border-dashed border-muted-foreground/25 p-6 text-center"
        >
          <p class="text-sm text-muted-foreground">
            Select a source type above to continue
          </p>
        </div>
      {/if}

      <!-- Chunking Method -->
      {#if formData.sourceType}
        <div class="space-y-3">
          <Label for="chunkingMethod" class="text-sm font-medium">Chunking Method</Label>
          <Select.Root
            type="single"
            name="chunkingMethod"
            bind:value={formData.chunkingMethod}
          >
            <Select.Trigger class="w-full">
              {formData.chunkingMethod
                ? chunkingMethods.find((m) => m.value === formData.chunkingMethod)?.label
                : "Select chunking method"}
            </Select.Trigger>
            <Select.Content>
              <Select.Group>
                <Select.Label>Chunking Methods</Select.Label>
                {#each chunkingMethods as method}
                  <Select.Item
                    value={method.value}
                    label={method.label}
                  >
                    <div class="flex flex-col">
                      <span class="font-medium">{method.label}</span>
                      <span class="text-xs text-muted-foreground mt-1">{method.description}</span>
                    </div>
                  </Select.Item>
                {/each}
              </Select.Group>
            </Select.Content>
          </Select.Root>
          
          {#if formData.chunkingMethod}
            <div class="p-3 bg-blue-50 border border-blue-200 rounded-md dark:bg-blue-950 dark:border-blue-800">
              <p class="text-xs text-blue-700 dark:text-blue-300">
                <strong>{chunkingMethods.find(m => m.value === formData.chunkingMethod)?.label}:</strong>
                {chunkingMethods.find(m => m.value === formData.chunkingMethod)?.description}
              </p>
            </div>
          {/if}
        </div>
      {/if}

      <!-- Name -->
      <div class="space-y-2">
        <Label for="name" class="text-sm font-medium">Name</Label>
        <Input
          id="name"
          bind:value={formData.name}
          placeholder="Enter a descriptive name"
        />
      </div>

      <!-- Description -->
      <div class="space-y-2">
        <Label for="description" class="text-sm font-medium">Description</Label>
        <Textarea
          id="description"
          bind:value={formData.description}
          placeholder="Provide a detailed description..."
          class="min-h-[80px] resize-y"
        />
      </div>

      <!-- Tag -->
      <div class="space-y-2">
        <Label for="tag" class="text-sm font-medium">Tag</Label>
        <Input
          id="tag"
          bind:value={formData.tag}
          placeholder="Add a category tag"
        />
      </div>
    </div>
    <Dialog.Footer class="gap-2">
      <Button variant="outline" onclick={() => (showAddModal = false)}
        >Cancel</Button
      >
      <Button
        onclick={handleAddSubmit}
        class="bg-green-600 hover:bg-green-700 text-white"
        disabled={isSubmitting ||
          !formData.sourceType ||
          !formData.name ||
          !formData.chunkingMethod ||
          (formData.sourceType === "file" && !formData.file) ||
          (formData.sourceType === "url" && !formData.url) ||
          (formData.sourceType === "text" && !formData.text)}
      >
        {#if isSubmitting}
          <div
            class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"
          ></div>
        {/if}
        {isSubmitting ? "Adding..." : "Add Knowledge"}
      </Button>
    </Dialog.Footer>
  </Dialog.Content>
</Dialog.Root>

<!-- Edit Knowledge Modal -->
<Dialog.Root bind:open={showEditModal}>
  <Dialog.Content class="max-w-md">
    <Dialog.Header>
      <Dialog.Title class="text-2xl font-semibold">Edit Knowledge</Dialog.Title>
      <Dialog.Description class="text-sm text-muted-foreground">
        Update the details for this knowledge item.
      </Dialog.Description>
    </Dialog.Header>

    {#if error}
      <div
        class="bg-destructive/10 border border-destructive/20 text-destructive px-3 py-2 rounded-md text-sm"
      >
        {error}
      </div>
    {/if}

    <div class="space-y-4 py-4">
      <!-- Name -->
      <div class="space-y-2">
        <Label for="editName" class="text-sm font-medium">Name</Label>
        <Input
          id="editName"
          bind:value={formData.name}
          placeholder="Enter a descriptive name"
        />
      </div>

      <!-- Description -->
      <div class="space-y-2">
        <Label for="editDescription" class="text-sm font-medium"
          >Description</Label
        >
        <Textarea
          id="editDescription"
          bind:value={formData.description}
          placeholder="Provide a detailed description..."
          class="min-h-[80px] resize-y"
        />
      </div>

      <!-- Tag -->
      <div class="space-y-2">
        <Label for="editTag" class="text-sm font-medium">Tag</Label>
        <Input
          id="editTag"
          bind:value={formData.tag}
          placeholder="Add a category tag"
        />
      </div>
    </div>
    <Dialog.Footer class="gap-2">
      <Button
        variant="outline"
        onclick={() => {
          showEditModal = false;
          error = "";
        }}
        disabled={isLoading}>Cancel</Button
      >
      <Button
        onclick={handleEditSubmit}
        class="bg-blue-600 hover:bg-blue-700 text-white"
        disabled={!formData.name.trim() || isLoading}
      >
        {#if isLoading}
          <svg
            class="animate-spin -ml-1 mr-3 h-4 w-4 text-current"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              class="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              stroke-width="4"
            ></circle>
            <path
              class="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            ></path>
          </svg>
          Updating...
        {:else}
          Update Knowledge
        {/if}
      </Button>
    </Dialog.Footer>
  </Dialog.Content>
</Dialog.Root>
