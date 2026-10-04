// Ordered migration list (DAT-01). Append new migrations; never edit or reorder shipped ones.
import m0001 from './0001-initial.js';

export const MIGRATIONS = Object.freeze([m0001]);
