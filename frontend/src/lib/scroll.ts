import { useEffect, useMemo, useRef, useState } from "react";

export type ActiveSectionRegister = (id: string) => (el: HTMLElement | null) => void;

export function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const mql = window.matchMedia?.("(prefers-reduced-motion: reduce)");
    if (!mql) return;
    const onChange = () => setReduced(Boolean(mql.matches));

    onChange();
    // Safari < 14
    if (typeof mql.addEventListener === "function") {
      mql.addEventListener("change", onChange);
      return () => mql.removeEventListener("change", onChange);
    }

    const legacy = mql as MediaQueryList & {
      addListener?: (listener: () => void) => void;
      removeListener?: (listener: () => void) => void;
    };

    // eslint-disable-next-line deprecation/deprecation
    legacy.addListener?.(onChange);
    // eslint-disable-next-line deprecation/deprecation
    return () => legacy.removeListener?.(onChange);
  }, []);

  return reduced;
}

interface UseActiveSectionOptions {
  /**
   * When the viewport middle crosses a section, it becomes active.
   * You can tune the threshold by adjusting rootMargin.
   */
  rootMargin?: string;
  /**
   * Higher threshold means more of the element must be visible to activate.
   */
  threshold?: number | number[];
  /**
   * Initial active section id (useful for SSR or deterministic default).
   */
  initialActiveId?: string;
}

export function useActiveSection(options: UseActiveSectionOptions = {}) {
  const { rootMargin = "-40% 0px -55% 0px", threshold = [0, 0.1, 0.25, 0.5, 0.75, 1], initialActiveId } = options;

  const [activeId, setActiveId] = useState<string | undefined>(initialActiveId);
  const elementsByIdRef = useRef(new Map<string, HTMLElement>());
  const latestActiveRef = useRef<string | undefined>(initialActiveId);

  const register = useMemo<ActiveSectionRegister>(() => {
    return (id: string) => (el: HTMLElement | null) => {
      const map = elementsByIdRef.current;
      if (!el) {
        map.delete(id);
        return;
      }
      map.set(id, el);
    };
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const map = elementsByIdRef.current;
    if (map.size === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        // Pick the most-visible intersecting entry.
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => (b.intersectionRatio ?? 0) - (a.intersectionRatio ?? 0));

        const next = visible[0]?.target as HTMLElement | undefined;
        const nextId = next?.dataset?.sectionId;

        if (nextId && nextId !== latestActiveRef.current) {
          latestActiveRef.current = nextId;
          setActiveId(nextId);
        }
      },
      { root: null, rootMargin, threshold }
    );

    map.forEach((el, id) => {
      el.dataset.sectionId = id;
      observer.observe(el);
    });

    return () => observer.disconnect();
  }, [rootMargin, threshold]);

  return { activeId, register };
}
