import { useCallback, useState } from "react";
import { Button } from "../../components";
import { Modal } from "../../components/Modal/Modal";
import { Form, Input } from "../../components/Form";
import { Block, Elem } from "../../utils/bem";
import WorkspaceSelector from "../CreateProject/WorkspaceSelector";
import { useAPI } from "../../providers/ApiProvider";

export const DuplicateProjectModal = ({ project, onClose }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [duplicateName, setDuplicateName] = useState(`${project.title} (Copy)`);
  const [selectedWorkspace, setSelectedWorkspace] = useState(project?.workspace?.id || "");
  const api = useAPI();

  const handleDuplicate = useCallback(
    async (e) => {
      e.preventDefault();
      if (!duplicateName.trim()) return;

      setIsLoading(true);
      try {
        // First, get the full project data
        const projectData = await api.callApi("project", {
          params: { pk: project.id },
        });

        // Prepare the new project data with safe serialization
        const newProjectData = {
          title: duplicateName.trim(),
          description: projectData.description || "",
          label_config: projectData.label_config || "",
          color: projectData.color || "",
          sampling: projectData.sampling || "Sequential sampling",
          workspace: selectedWorkspace || null,
          // Copy other relevant settings with safe defaults
          show_instruction: Boolean(projectData.show_instruction),
          show_skip_button: Boolean(projectData.show_skip_button),
          enable_empty_annotation: Boolean(projectData.enable_empty_annotation),
          show_annotation_history: Boolean(projectData.show_annotation_history),
          reveal_preannotations_interactively: Boolean(projectData.reveal_preannotations_interactively),
          show_collab_predictions: Boolean(projectData.show_collab_predictions),
          evaluate_predictions_automatically: Boolean(projectData.evaluate_predictions_automatically),
          is_published: false, // Set to false for duplicated projects
          // Safely handle complex objects
          control_weights: projectData.control_weights ? 
            JSON.parse(JSON.stringify(projectData.control_weights)) : {},
          // Only include simple, serializable fields
          maximum_annotations: projectData.maximum_annotations || 1,
          min_annotations_to_start_training: projectData.min_annotations_to_start_training || 0,
        };

        // Remove any undefined or null values that might cause serialization issues
        Object.keys(newProjectData).forEach(key => {
          if (newProjectData[key] === undefined) {
            delete newProjectData[key];
          }
        });

        console.log('Creating project with data:', newProjectData);

        // Create the new project
        const newProject = await api.callApi("createProject", {
          body: newProjectData,
        });

        // Close modal and potentially refresh the projects list
        onClose(newProject);

        // Reload the page to show the new project
        window.location.reload();
      } catch (error) {
        console.error("Failed to duplicate project:", error);
        
        // Enhanced error handling with user feedback
        let errorMessage = "Failed to duplicate project. ";
        
        if (error.response) {
          // Server responded with error status
          const status = error.response.status;
          const data = error.response.data;
          
          if (status === 400) {
            if (data && typeof data === 'object') {
              // Extract specific field errors
              const fieldErrors = Object.entries(data)
                .map(([field, errors]) => `${field}: ${Array.isArray(errors) ? errors.join(', ') : errors}`)
                .join('; ');
              errorMessage += fieldErrors || "Invalid data format.";
            } else {
              errorMessage += "Invalid data format. Please check the project configuration.";
            }
          } else if (status === 403) {
            errorMessage += "You don't have permission to create projects.";
          } else if (status === 409) {
            errorMessage += "A project with this name already exists.";
          } else {
            errorMessage += `Server error (${status}). Please try again.`;
          }
        } else if (error.request) {
          // Network error
          errorMessage += "Network error. Please check your connection and try again.";
        } else {
          // Other error
          errorMessage += error.message || "An unexpected error occurred.";
        }
        
        // TODO: Replace with proper toast notification
        alert(errorMessage);
      } finally {
        setIsLoading(false);
      }
    },
    [project.id, duplicateName, selectedWorkspace, api, onClose],
  );

  const handleModalClick = useCallback((e) => {
    // Prevent clicks from bubbling up to parent elements
    e.stopPropagation();
  }, []);

  return (
    <Modal title="Duplicate Project" visible={true} onClose={onClose} style={{ width: 480 }}>
      <Block name="duplicate-project-modal" onClick={handleModalClick}>
        <Form onSubmit={handleDuplicate}>
          <Form.Row columnCount={1} rowGap="16px">
            <Input
              label="Project Name"
              value={duplicateName}
              onChange={(e) => setDuplicateName(e.target.value)}
              placeholder="Enter project name"
              required
            />

            <Block name="workspace-section">
              <Elem name="title" tag="label">
                Workspace
              </Elem>
              <WorkspaceSelector value={selectedWorkspace} onChange={setSelectedWorkspace} />
            </Block>
          </Form.Row>

          <Form.Actions>
            <Button type="button" look="alt" onClick={onClose} disabled={isLoading}>
              Cancel
            </Button>
            <Button
              type="submit"
              look="primary"
              loading={isLoading ? "true" : undefined}
              disabled={!duplicateName.trim()}
            >
              {isLoading ? "Duplicating..." : "Duplicate Project"}
            </Button>
          </Form.Actions>
        </Form>
      </Block>
    </Modal>
  );
};
