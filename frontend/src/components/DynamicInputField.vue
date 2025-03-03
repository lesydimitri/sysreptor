<template>
  <div :id="props.id" class="mt-4">
    <!-- String -->
    <markdown-text-field
      v-if="definition.type === 'string'"
      v-model="formValue"
      :spellcheck-supported="definition.spellcheck"
      v-bind="fieldAttrs"
    />

    <!-- Markdown -->
    <markdown-field
      v-else-if="definition.type === 'markdown'"
      v-model="formValue"
      v-bind="fieldAttrs"
    />

    <!-- Date -->
    <s-date-picker
      v-else-if="definition.type === 'date'"
      v-model="formValue"
      :locale="props.lang || undefined"
      v-bind="fieldAttrs"
    />

    <!-- Enum -->
    <s-autocomplete
      v-else-if="definition.type === 'enum'"
      v-model="formValue"
      :items="[{value: null as string|null, label: '---'}].concat(definition.choices!)"
      item-title="label"
      item-value="value"
      clearable
      v-bind="fieldAttrs"
    />

    <!-- Combobox -->
    <s-combobox
      v-else-if="definition.type === 'combobox'"
      v-model="formValue"
      :items="definition.suggestions"
      clearable
      spellcheck="false"
      v-bind="fieldAttrs"
    />

    <!-- Number -->
    <s-text-field
      v-else-if="definition.type === 'number'"
      :model-value="formValue"
      @update:model-value="emitUpdate(parseFloat($event))"
      type="number"
      v-bind="fieldAttrs"
    />

    <!-- Boolean -->
    <s-checkbox
      v-else-if="definition.type === 'boolean'"
      :model-value="formValue || false"
      @update:model-value="emitUpdate($event)"
      v-bind="fieldAttrs"
    />

    <!-- CVSS -->
    <s-cvss-field
      v-else-if="definition.type === 'cvss'"
      v-model="formValue"
      v-bind="fieldAttrs"
    />

    <!-- User -->
    <s-user-selection
      v-else-if="definition.type === 'user'"
      v-model="formValue"
      :selectable-users="selectableUsers"
      v-bind="fieldAttrs"
    />

    <!-- Object -->
    <s-card v-else-if="definition.type === 'object'">
      <v-card-title class="text-body-1">{{ label }}</v-card-title>

      <v-card-text>
        <dynamic-input-field
          v-for="(objectFieldDefinition, objectFieldId) in definition.properties"
          :key="objectFieldId"
          :model-value="formValue[objectFieldId]"
          @update:model-value="emitInputObject(objectFieldId as string, $event)"
          :definition="objectFieldDefinition"
          :id="props.id ? (props.id + '.' + objectFieldId) : undefined"
          :show-field-ids="showFieldIds"
          :selectable-users="selectableUsers"
          v-bind="fieldAttrs"
        />
      </v-card-text>
    </s-card>

    <!-- List -->
    <s-card v-else-if="definition.type === 'list'">
      <v-card-title class="text-body-1">
        <div class="d-flex flex-row">
          <span>{{ label }}</span>

          <template v-if="definition.items!.type === 'string'">
            <v-spacer />
            <s-btn
              @click="bulkEditList = !bulkEditList"
              icon
              variant="text"
              density="comfortable"
            >
              <v-icon v-if="bulkEditList" icon="mdi-format-list-bulleted" />
              <v-icon v-else icon="mdi-playlist-edit" />
              <s-tooltip activator="parent">
                <span v-if="bulkEditList">Edit as list</span>
                <span v-else>Bulk edit list items</span>
              </s-tooltip>
            </s-btn>
          </template>
        </div>
      </v-card-title>

      <v-card-text>
        <!-- Bulk edit list items of list[string] -->
        <v-textarea
          v-if="definition.items!.type === 'string' && bulkEditList"
          :model-value="(formValue || []).join('\n')"
          @update:model-value="emitInputStringList"
          auto-grow
          hide-details="auto"
          spellcheck="false"
          variant="outlined"
          v-bind="fieldAttrs"
          label="Enter one item per line"
          class="mt-4"
        />
        <v-list v-else class="pa-0">
          <v-list-item v-for="(entryVal, entryIdx) in formValue" :key="entryIdx" class="pa-0">
            <template #default>
              <dynamic-input-field
                :model-value="entryVal"
                @update:model-value="emitInputList('update', entryIdx as number, $event)"
                :definition="definition.items!"
                :id="id ? (id + '[' + entryIdx + ']') : undefined"
                :show-field-ids="showFieldIds"
                :selectable-users="selectableUsers"
                v-bind="fieldAttrs"
              />
            </template>
            <template #append>
              <btn-delete
                :delete="() => emitInputList('delete', entryIdx as number)"
                :confirm="!isEmptyOrDefault(entryVal, definition.items!)"
                :disabled="props.disabled"
                button-variant="icon"
              />
            </template>
          </v-list-item>

          <v-list-item class="pa-0">
            <s-btn
              @click="emitInputList('add')"
              color="secondary"
              :disabled="props.disabled"
              prepend-icon="mdi-plus"
              text="Add"
            />
          </v-list-item>
        </v-list>
      </v-card-text>
    </s-card>

    <div v-else>
      {{ definition }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { FieldDefinition, UserShortInfo } from "~/utils/types";
import { MarkdownProps } from "~/composables/markdown";

const props = defineProps<MarkdownProps & {
  modelValue?: any;
  definition: FieldDefinition;
  id?: string;
  showFieldIds?: boolean;
  selectableUsers?: UserShortInfo[];
  disabled?: boolean;
  autofocus?: boolean;
}>();
const emit = defineEmits<{
  (e: 'update:modelValue', value: any): void;
}>();

function getInitialValue(fieldDef: FieldDefinition, useDefault = true): any {
  if (fieldDef.default && useDefault) {
    return fieldDef.default;
  } else if (fieldDef.type === "list") {
    return [];
  } else if (fieldDef.type === 'object') {
    return Object.fromEntries(Object.entries(fieldDef.properties!).map(([f, d]) => [f, getInitialValue(d, useDefault)]));
  } else {
    return null;
  }
}
function emitUpdate(val: any) {
  emit('update:modelValue', val);
}
function emitInputObject(objectFieldId: string, val: any) {
  emitUpdate({ ...formValue.value, [objectFieldId]: val });
}
function emitInputList(action: string, entryIdx?: number, entryVal: any|null = null) {
  const newVal = [...formValue.value];
  if (action === "update") {
    newVal[entryIdx!] = entryVal;
  } else if (action === "delete") {
    newVal.splice(entryIdx!, 1);
  } else if (action === 'add') {
    if (entryVal === null) {
      entryVal = getInitialValue(props.definition.items!);
    }

    newVal.push(entryVal);
  }
  emitUpdate(newVal);
}

const formValue = computed({
  get: () => {
    if (props.modelValue === null || props.modelValue === undefined) {
      return getInitialValue(props.definition, false);
    }
    return props.modelValue;
  },
  set: val => emitUpdate(val),
});
const label = computed(() => {
  let out = props.definition.label || '';
  if (props.showFieldIds && props.id) {
    if (out) {
      out += ' (' + props.id + ')';
    } else {
      out = props.id;
    }
  }
  return out;
})

function isEmptyOrDefault(value: any, definition: FieldDefinition): boolean {
  if (definition.type === 'list') {
    return value.length === 0 || value.every((v: any) => isEmptyOrDefault(v, definition.items!));
  } else if (definition.type === 'object') {
    return !value || Object.entries(definition.properties!).every(([k, d]) => isEmptyOrDefault(value[k], d));
  } else {
    return !value || value === definition.default;
  }
}

const bulkEditList = ref(false);
function emitInputStringList(valuesListString?: string) {
  const values = (valuesListString || '').split('\n').filter(v => !!v);
  emitUpdate(values);
}

const attrs = useAttrs();
const fieldAttrs = computed(() => ({
  ...attrs,
  label: label.value,
  disabled: props.disabled,
  autofocus: props.autofocus,
  lang: props.lang,
  uploadFile: props.uploadFile,
  rewriteFileUrl: props.rewriteFileUrl,
  rewriteReferenceLink: props.rewriteReferenceLink,
}))
</script>
