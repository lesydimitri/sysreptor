<template>
  <s-autocomplete v-bind="autocompleteAttrs">
    <template #append-item v-if="!props.selectableUsers && allItems.length > 0">
      <page-loader :items="items" />
    </template>
    <template #no-data v-if="!props.selectableUsers && allItems.length === 0 && items.hasNextPage.value">
      <page-loader :items="items" />
    </template>
    <template v-if="props.multiple" #chip="chipSlotData">
      <slot name="chip" v-bind="chipSlotData">
        <v-chip v-bind="chipSlotData.props" :disabled="false" />
      </slot>
    </template>
    <template #append-inner><slot name="append-inner" /></template>
  </s-autocomplete>
</template>

<script setup lang="ts">
import isObject from "lodash/isObject";
import sortBy from "lodash/sortBy"
import uniqBy from "lodash/uniqBy"

const props = withDefaults(defineProps<{
  modelValue: UserShortInfo|UserShortInfo[]|null;
  label?: string;
  required?: boolean;
  disabled?: boolean;
  multiple?: boolean;
  clearable?: boolean;
  preventUnselectingSelf?: boolean;
  selectableUsers?: UserShortInfo[]|null;
}>(), {
  label: 'Users',
  required: false,
  multiple: false,
  clearable: true,
  preventUnselectingSelf: false,
  selectableUsers: null,
});
const emit = defineEmits<{
  (e: 'update:modelValue', value: UserShortInfo|UserShortInfo[]|null): void,
}>();

const auth = useAuth();

const items = useSearchableCursorPaginationFetcher<UserShortInfo>({
  baseURL: '/api/v1/pentestusers/',
  query: {
    ordering: 'username',
  }
});
const rules = {
  single: [(v: UserShortInfo|null) => !!v || 'Item is required'],
  multiple: [(v: UserShortInfo[]|null) => (v && v.length > 0) || 'Item is required'],
};

const initialUsers = ref<UserShortInfo[]>([]);
if (props.modelValue && !props.selectableUsers) {
  if (Array.isArray(props.modelValue)) {
    initialUsers.value = props.modelValue;
  } else if (isObject(props.modelValue)) {
    initialUsers.value = [props.modelValue];
  }
}

const allItems = computed(() => {
  if (props.selectableUsers) {
    return sortBy(props.selectableUsers, [u => u.username || u.name]);
  }
  return uniqBy(initialUsers.value.concat(items.data.value), 'id');
})

const attrs = useAttrs();
const autocompleteAttrs = computed(() =>
  Object.assign({}, attrs, {
    modelValue: props.modelValue,
    'onUpdate:modelValue': (e: any) => emit('update:modelValue', e),
    label: props.label,
    hideNoData: false,
    items: allItems.value,
    itemValue: 'id',
    itemTitle: (u: UserShortInfo) => (u.username && u.name) ? `${u.username} (${u.name})` : (u.username || u.name || 'Unknown User'),
    itemProps: (u: UserShortInfo) => {
      const preventUnselect = props.preventUnselectingSelf && u.id === auth.user.value!.id && (Array.isArray(props.modelValue) && props.modelValue.some(v => v.id === u.id));
      return {
        disabled: preventUnselect,
        closable: !preventUnselect,
      };
    },
    disabled: props.disabled,
    returnObject: true,
    clearable: props.clearable,
  },
  props.multiple ? {
    multiple: true,
    chips: true,
  } : {},
  props.required ? {
    rules: props.multiple ? rules.multiple : rules.single,
  } : {})
);

</script>

<style lang="scss" scoped>
:deep(.v-field--variant-underlined .v-label.v-field-label--floating) {
  transform: translateY(-10px);
}
</style>
