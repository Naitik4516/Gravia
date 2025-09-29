export const categories = {
    general: "⚙️ General",
    conversation: "💬 Conversation",
    personalization: "✨ Personalization",
    configuration: "🛠️ Configuration",
    integrations: "🧩 Integrations",
    safety_and_security: "🛡️ Safety & Security",
    keyboard_shortcuts: "⌨️ Keyboard Shortcuts"
};

export type SettingType = 'boolean' | 'toggle' | 'string' | 'password' | 'number' | 'select' | 'list' | 'shortcut' | 'combobox' | 'integration' | 'text';

export interface SettingItem {
    label: string;
    key: string;
    type: SettingType;
    value: any;
    description?: string;
    options?: string[] | 'dynamic_voices';
    dynamic_options?: string;
    labels?: { true: string; false: string };
    min?: number;
    max?: number;
    parent?: string;
    condition?: string | string[];
    condition_type?: 'equals' | 'in';
}

/**
 * Evaluates whether a child field should be visible based on its parent field's value
 */
export function shouldShowField(field: SettingItem, parentValues: Record<string, any>): boolean {
    // If no parent field, always show
    if (!field.parent) {
        return true;
    }

    const parentValue = parentValues[field.parent];

    // If parent field has no value, hide child
    if (parentValue === undefined || parentValue === null) {
        return false;
    }

    // If no condition specified, show if parent has any value
    if (!field.condition) {
        return true;
    }

    const conditionType = field.condition_type || 'equals';

    if (conditionType === 'equals') {
        return parentValue === field.condition;
    } else if (conditionType === 'in') {
        const conditions = Array.isArray(field.condition) ? field.condition : [field.condition];
        return conditions.includes(parentValue);
    }

    return false;
}

/**
 * Creates a map of field keys to their current values for easy lookup
 */
export function createParentValueMap(settings: SettingItem[]): Record<string, any> {
    return settings.reduce((map, setting) => {
        map[setting.key] = setting.value;
        return map;
    }, {} as Record<string, any>);
}
