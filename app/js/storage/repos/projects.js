// Projects repository (DAT-02).
import { makeRepo } from './make-repo.js';
import { validateProject } from '../../domain/validate.js';

export const projectsRepo = makeRepo('projects', validateProject);
