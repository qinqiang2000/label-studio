import { useCallback, useState } from "react";
import { Button } from "../../components";
import { Modal } from "../../components/Modal/Modal";
import { Input } from "../../components/Form";
import { Block, Elem } from "../../utils/bem";
import { useToast, ToastType } from "@humansignal/ui";
import { Caption } from "../../components/Caption/Caption";
import WorkspaceSelector from "../CreateProject/WorkspaceSelector";
import "./DuplicateProjectModal.scss";

// Helper function to duplicate project using backend API
const duplicateProject = async (projectId, title, workspaceId) => {
  console.log(`📋 Starting project duplication: ${projectId}`);

  try {
    // Use fetch directly to call the new backend duplicate API
    const response = await fetch(`/api/projects/${projectId}/duplicate/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({
        title: title,
        workspace: workspaceId || null,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }

    const result = await response.json();
    console.log(`✅ Project duplication successful:`, result);
    return result;
  } catch (error) {
    console.error("❌ Project duplication failed:", error);
    throw error;
  }
};

export const DuplicateProjectModal = ({ project, onClose }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [loadingStage, setLoadingStage] = useState("");
  const [duplicateName, setDuplicateName] = useState(`${project.title} (Copy)`);
  const [selectedWorkspace, setSelectedWorkspace] = useState(project?.workspace?.id || "");
  const toast = useToast();

  const handleDuplicate = useCallback(async () => {
    if (!duplicateName.trim()) return;

    setIsLoading(true);
    setLoadingStage("Duplicating project...");
    try {
      // Use the new backend duplicate API
      const result = await duplicateProject(project.id, duplicateName.trim(), selectedWorkspace);

      console.log("✅ Duplication completed:", result);

      // Show success toast message with copy stats
      let successMessage = `Project "${duplicateName}" created successfully!`;
      if (result.task_count > 0) {
        successMessage += ` Copied ${result.task_count} task${result.task_count > 1 ? "s" : ""}`;
        if (result.annotation_count > 0) {
          successMessage += ` and ${result.annotation_count} annotation${result.annotation_count > 1 ? "s" : ""}`;
        }
        if (result.prediction_count > 0) {
          successMessage += ` and ${result.prediction_count} prediction${result.prediction_count > 1 ? "s" : ""}`;
        }
      }
      successMessage += `.`;

      // Use toast instead of alert
      toast?.show({
        message: successMessage,
        type: ToastType.info,
        duration: 4000,
      });

      // Close modal and trigger refresh with the new project data
      onClose({
        id: result.id,
        title: result.title,
      });
    } catch (error) {
      console.error("Project duplication failed:", error);

      // Simple error handling with toast
      let errorMessage = "Project duplication failed.";

      if (error.message) {
        if (error.message.includes("400")) {
          errorMessage += " Please check the project name and workspace settings.";
        } else if (error.message.includes("403")) {
          errorMessage += " You don't have permission to duplicate this project.";
        } else if (error.message.includes("404")) {
          errorMessage += " Project not found or has been deleted.";
        } else if (error.message.includes("500")) {
          errorMessage += " Server error, please try again later.";
        } else {
          errorMessage += ` ${error.message}`;
        }
      } else {
        errorMessage += " An unknown error occurred, please try again later.";
      }

      // Use toast instead of alert
      toast?.show({
        message: errorMessage,
        type: ToastType.error,
        duration: 6000,
      });
    } finally {
      setIsLoading(false);
      setLoadingStage("");
    }
  }, [project.id, duplicateName, selectedWorkspace, onClose, toast]);

  const handleModalClick = useCallback((e) => {
    // Prevent clicks from bubbling up to parent elements
    e.stopPropagation();
  }, []);

  return (
    <Modal title="Duplicate Project" visible={true} onClose={onClose} style={{ width: 520 }}>
      <Block name="duplicate-project-modal" onClick={handleModalClick}>
        {/* <Block name="form-content"> */}
        <Block name="form-section" mod={{ spacing: "normal" }}>
          <Block name="form-field">
            <Elem name="label" tag="label">
              Project Name
            </Elem>
            <Input
              value={duplicateName}
              onChange={(e) => setDuplicateName(e.target.value)}
              placeholder="Enter project name"
              required
            />
          </Block>

          <Block name="workspace-section">
            <Elem name="badge-wrapper">
              <Elem name="title">Workspace</Elem>
            </Elem>
            <WorkspaceSelector
              value={selectedWorkspace || ""}
              onChange={(value) => setSelectedWorkspace(value || null)}
            />
            <Caption>Organize your projects by grouping them into workspaces.</Caption>
          </Block>
        </Block>

        <Block name="form-actions">
          <Button type="button" look="alt" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button
            type="button"
            look="primary"
            onClick={handleDuplicate}
            loading={isLoading ? "true" : undefined}
            disabled={!duplicateName.trim()}
          >
            {isLoading ? loadingStage || "Duplicating..." : "Duplicate Project"}
          </Button>
        </Block>
      </Block>
      {/* </Block> */}
    </Modal>
  );
};
