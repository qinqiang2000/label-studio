import type React from "react";
import { useCallback, useState } from "react";
import { Block, Elem } from "../../utils/bem";
import { Button } from "@humansignal/ui";
import { Input, TextArea } from "../../components/Form/Elements";
import { useAPI } from "../../providers/ApiProvider";
import "./CreateWorkspaceModal.scss";

interface Workspace {
  id: number;
  name: string;
  description: string;
  color: string;
  is_archived: boolean;
}

interface EditWorkspaceModalProps {
  workspace: Workspace;
  onClose: () => void;
  onWorkspaceUpdated: () => void;
}

const defaultColors = [
  "#1976d2",
  "#dc004e",
  "#9c27b0",
  "#673ab7",
  "#3f51b5",
  "#2196f3",
  "#03a9f4",
  "#00bcd4",
  "#009688",
  "#4caf50",
  "#8bc34a",
  "#cddc39",
  "#ffeb3b",
  "#ffc107",
  "#ff9800",
  "#ff5722",
];

export const EditWorkspaceModal: React.FC<EditWorkspaceModalProps> = ({ workspace, onClose, onWorkspaceUpdated }) => {
  const [name, setName] = useState(workspace.name);
  const [description, setDescription] = useState(workspace.description);
  const [color, setColor] = useState(workspace.color);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const api = useAPI();

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();

      if (!name.trim()) {
        alert("Please provide a workspace name");
        return;
      }

      try {
        setIsSubmitting(true);
        await api.callApi("updateWorkspace", {
          params: { pk: workspace.id },
          body: {
            name: name.trim(),
            description: description.trim(),
            color,
          },
        });

        onWorkspaceUpdated();
      } catch (error) {
        console.error("Failed to update workspace:", error);
        alert("Failed to update workspace. Please try again.");
      } finally {
        setIsSubmitting(false);
      }
    },
    [name, description, color, api, workspace.id, onWorkspaceUpdated, onClose],
  );

  return (
    <Block name="create-workspace-modal">
      <form onSubmit={handleSubmit}>
        <Elem name="form-group">
          <label htmlFor="workspace-name">Name *</label>
          <Input
            id="workspace-name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Enter workspace name"
            disabled={isSubmitting}
            required
            className="project-title w-full"
          />
        </Elem>

        <Elem name="form-group">
          <label htmlFor="workspace-description">Description</label>
          <TextArea
            id="workspace-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Enter workspace description (optional)"
            disabled={isSubmitting}
            rows={4}
            style={{ minHeight: 100 }}
            className="project-description w-full"
          />
        </Elem>

        <Elem name="form-group">
          <label>Color</label>
          <Elem name="color-picker">
            {defaultColors.map((colorOption) => (
              <Elem
                key={colorOption}
                name="color-option"
                mod={{ selected: color === colorOption }}
                style={{ backgroundColor: colorOption, position: "relative" }}
                onClick={() => !isSubmitting && setColor(colorOption)}
              >
                {color === colorOption && (
                  <svg
                    width="20"
                    height="20"
                    viewBox="0 0 20 20"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                    style={{
                      position: "absolute",
                      top: "50%",
                      left: "50%",
                      transform: "translate(-50%, -50%)",
                      pointerEvents: "none",
                      zIndex: 2,
                    }}
                  >
                    <circle cx="10" cy="10" r="9" fill="rgba(0,0,0,0.18)" />
                    <path
                      d="M6 10.5L9 13.5L14 8.5"
                      stroke="#fff"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                )}
              </Elem>
            ))}
          </Elem>
        </Elem>

        <Elem name="actions">
          <Button type="button" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button type="submit" look="primary" disabled={isSubmitting || !name.trim()}>
            {isSubmitting ? "Updating..." : "Update Workspace"}
          </Button>
        </Elem>
      </form>
    </Block>
  );
};
