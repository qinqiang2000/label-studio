import { useCallback, useState, useEffect } from "react";
import { dismissTip, getRandomTip, getTipEvent, getTipMetadata } from "./utils";
import type { Tip, TipsCollection } from "./types";

export const useRandomTip = (collection: keyof TipsCollection) => {
  const [tip, setTip] = useState<Tip | null>(null);

  useEffect(() => {
    getRandomTip(collection).then(setTip);
  }, [collection]);

  const dismiss = useCallback(() => {
    dismissTip(collection);
    setTip(null);
  }, [collection]);

  const onLinkClick = useCallback(() => {
    if (tip) {
      __lsa(getTipEvent(collection, tip, "click"), getTipMetadata(tip));
    }
  }, [tip, collection]);

  return [tip, dismiss, onLinkClick] as const;
};
