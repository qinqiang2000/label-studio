import React, { useCallback } from "react";
import { useAPI } from "../../../providers/ApiProvider";
import { unique } from "../../../utils/helpers";
import { importFiles } from "./utils";

const DEFAULT_COLUMN = "$undefined$";

export const useImportPage = (project, sample, onImportComplete) => {
  const [uploading, setUploadingStatus] = React.useState(false);
  const [fileIds, setFileIds] = React.useState([]);
  const [_columns, _setColumns] = React.useState([]);
  const addColumns = (cols) => _setColumns((current) => unique(current.concat(cols)));
  // undefined - no csv added, all good, keep moving
  // choose - csv added, block modal until user chooses a way to hangle csv
  // tasks | ts — choice made, all good, this cannot be undone
  const [csvHandling, setCsvHandling] = React.useState(); // undefined | choose | tasks | ts

  // New state for conflict handling
  const [mergeStrategy, setMergeStrategy] = React.useState("create_new");

  const uploadDisabled = csvHandling === "choose";
  const api = useAPI();

  // don't use columns from csv if we'll not use it as csv
  const columns = ["choose", "ts"].includes(csvHandling) ? [DEFAULT_COLUMN] : _columns;

  const checkForConflicts = useCallback(async () => {
    if (!fileIds.length) return { conflicts: [], conflict_count: 0 };

    try {
      const conflictResult = await api.callApi("checkImportConflicts", {
        params: {
          pk: project.id,
        },
        body: {
          file_upload_ids: fileIds,
          files_as_tasks_list: csvHandling === "tasks",
        },
      });

      return conflictResult;
    } catch (error) {
      console.error("Error checking for conflicts:", error);
      return { conflicts: [], conflict_count: 0 };
    }
  }, [fileIds, project.id, csvHandling, api]);

  const finishUpload = useCallback(async (skipConflictCheck = false) => {
    setUploadingStatus(true);

    try {
      // Check for conflicts first unless explicitly skipped
      if (!skipConflictCheck && fileIds.length) {
        const conflictResult = await checkForConflicts();

        if (conflictResult.conflict_count > 0) {
          const userChoice = window.confirm(
            `Found ${conflictResult.conflict_count} task(s) with matching IDs that already exist in this project.\n\n` +
            `Conflicting task IDs: ${conflictResult.conflicts.join(', ')}\n\n` +
            `MERGE (OK): Updates existing tasks. For predictions/annotations:\n` +
            `  • Same ID: Updates the existing record\n` +
            `  • New/Different ID: Creates new record\n` +
            `  • Note: Duplicates blocked by (task+model_version+prompt_name) constraint\n\n` +
            `CREATE NEW (Cancel): Imports as new tasks with auto-generated IDs`
          );

          const strategy = userChoice ? "merge" : "create_new";
          setMergeStrategy(strategy);

          // Continue with the selected strategy
          const result = await api.callApi("reimportFiles", {
            params: {
              pk: project.id,
            },
            body: {
              file_upload_ids: fileIds,
              files_as_tasks_list: csvHandling === "tasks",
              merge_strategy: strategy,
            },
          });

          setUploadingStatus(false);
          return result;
        }
      }

      const imported = await api.callApi("reimportFiles", {
        params: {
          pk: project.id,
        },
        body: {
          file_upload_ids: fileIds,
          files_as_tasks_list: csvHandling === "tasks",
          merge_strategy: mergeStrategy,
        },
      });

      setUploadingStatus(false);
      return imported;
    } catch (error) {
      setUploadingStatus(false);
      throw error;
    }
  }, [fileIds, checkForConflicts, api, project.id, csvHandling, mergeStrategy]);

  const uploadSample = useCallback(
    async (sample, onStart, onFinish) => {
      onStart?.();
      const url = sample.url;
      const body = new URLSearchParams({ url });
      await importFiles({
        files: [{ name: url }],
        body,
        project,
      });
      onFinish?.();
    },
    [project],
  );


  const pageProps = {
    onWaiting: setUploadingStatus,
    // onDisableSubmit: onDisableSubmit,
    highlightCsvHandling: uploadDisabled,
    addColumns,
    csvHandling,
    setCsvHandling,
    onFileListUpdate: setFileIds,
    dontCommitToProject: true,
  };

  return {
    columns,
    uploading,
    uploadDisabled,
    finishUpload,
    fileIds,
    pageProps,
    uploadSample,
  };
};
