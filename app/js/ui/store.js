// Application state store (UI-02). Plain object state, replaced (never mutated) on update.
// Pure: no DOM, so it is unit-tested with node --test.

export function createStore(initial = {}) {
  let state = Object.freeze({ ...initial });
  const subscribers = new Set();

  return {
    getState() {
      return state;
    },
    // Shallow-merge `patch` into a new frozen state, then notify subscribers with (state, previous).
    // A failing subscriber does not stop the others; the first error is re-thrown afterwards.
    update(patch) {
      const previous = state;
      state = Object.freeze({ ...state, ...patch });
      let firstError = null;
      for (const fn of [...subscribers]) {
        try {
          fn(state, previous);
        } catch (err) {
          firstError ??= err;
        }
      }
      if (firstError) throw firstError;
      return state;
    },
    // Returns a function that removes the subscription.
    subscribe(fn) {
      if (typeof fn !== 'function') throw new TypeError('subscriber must be a function');
      subscribers.add(fn);
      return () => subscribers.delete(fn);
    },
  };
}

const appStore = createStore({ route: null });

export const getState = () => appStore.getState();
export const update = (patch) => appStore.update(patch);
export const subscribe = (fn) => appStore.subscribe(fn);
