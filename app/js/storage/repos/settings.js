// Settings repository (DAT-02). One record per setting: { key, value, schema, updatedAt }.
// Never holds secrets: the validator refuses key/token/secret/password names.
import { makeRepo } from './make-repo.js';
import { validateSettings } from '../../domain/validate.js';

export const settingsRepo = makeRepo('settings', validateSettings);
