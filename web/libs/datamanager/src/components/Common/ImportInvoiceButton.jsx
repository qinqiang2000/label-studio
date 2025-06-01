import React, { useCallback } from "react";
import { Button } from "./Button/Button";

export const ImportInvoiceButton = ({ size, ...props }) => {
  const invokeAction = useCallback(() => {
    if (window.APP_SETTINGS?.debug) {
      console.log("Import Invoice button clicked");
    }
    const dm = window.dataManager;
    if (dm && dm.invoke) {
      dm.invoke("importInvoiceClicked");
    }
  }, []);

  return (
    <Button onClick={invokeAction} size={size} look="primary" {...props}>
      Import Invoice
    </Button>
  );
};

ImportInvoiceButton.displayName = "ImportInvoiceButton"; 