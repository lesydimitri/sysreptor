<template>
  <v-container fluid class="pt-0 h-100 overflow-y-auto">
    <v-form ref="form">
      <edit-toolbar :form="$refs.form" :save="performCreate" save-button-text="Create User">
        <template #title>Create new User</template>
      </edit-toolbar>

      <user-info-form v-model="userForm" :errors="serverErrors" :can-edit-permissions="true" :can-edit-username="true">
        <template #login-information>
          <s-password-field
            v-if="apiSettings.isLocalUserAuthEnabled"
            v-model="userForm.password"
            confirm show-strength
            :error-messages="serverErrors?.password || []"
          />
          <div v-if="apiSettings.isSsoEnabled" class="mt-4">
            SSO Authentication Identity (optional):
            <v-row>
              <v-col>
                <s-select
                  v-model="identityForm.provider"
                  label="Provider"
                  :items="apiSettings.ssoAuthProviders"
                  item-value="id"
                  item-title="name"
                />
              </v-col>
              <v-col>
                <s-text-field
                  v-model="identityForm.identifier"
                  label="Identifier"
                  spellcheck="false"
                />
              </v-col>
            </v-row>
          </div>
        </template>
      </user-info-form>
    </v-form>
  </v-container>
</template>
<script setup lang="ts">
import type { VForm } from "vuetify/lib/components/index.mjs";

const apiSettings = useApiSettings();

const userForm = ref<User & { password: string|null }>({
  username: null,
  password: null,
  title_before: null,
  first_name: '',
  middle_name: null,
  last_name: '',
  title_after: null,
  email: null,
  phone: null,
  mobile: null,
  is_superuser: !apiSettings.isProfessionalLicense,
  is_user_manager: false,
  is_designer: false,
  is_template_editor: false,
  is_guest: false,
  is_system_user: false,
  is_global_archiver: false,
} as any);
const identityForm = ref({
  provider: null,
  identifier: null
});
const serverErrors = ref<any|null>();

const form = ref<VForm>();
async function performCreate() {
  try {
    const user = await $fetch<User>('/api/v1/pentestusers/', {
      method: 'POST',
      body: userForm.value,
    });

    if (identityForm.value.provider && identityForm.value.identifier) {
      try {
        await $fetch(`/api/v1/pentestusers/${user.id}/identities/`, {
          method: 'POST',
          body: identityForm.value,
        })
      } catch (error) {
        requestErrorToast({ error });
      }
    }
    await navigateTo(`/users/${user.id}/`)
  } catch (error: any) {
    if (error?.status === 400 && error?.data) {
      serverErrors.value = error.data;
    } else {
      requestErrorToast({ error });
    }
  }
}
</script>
