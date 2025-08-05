import type React from "react";
import { Block, Elem } from "../../utils/bem";
import { Button } from "@humansignal/ui";
import { IconChevron } from "@humansignal/icons";
import { WorkspaceCard } from "./WorkspaceCard";

interface Workspace {
  id: number;
  name: string;
  description: string;
  color: string;
  is_archived: boolean;
  member_count: number;
  project_count: number;
  created_by: {
    id: number;
    email: string;
    first_name: string;
    last_name: string;
  };
  created_at: string;
  updated_at: string;
}

interface WorkspaceArchivedProps {
  workspaces: Workspace[];
  isExpanded: boolean;
  onToggle: () => void;
  onUpdate: () => void;
  currentUser?: {
    is_superuser?: boolean;
  } | null;
}

export const WorkspaceArchived: React.FC<WorkspaceArchivedProps> = ({
  workspaces,
  isExpanded,
  onToggle,
  onUpdate,
  currentUser,
}) => {
  return (
    <Block name="workspace-archived">
      <Elem name="header" onClick={onToggle}>
        <Elem name="title">Archived Workspaces ({workspaces.length})</Elem>
        <Button size="small" look="alt">
          <IconChevron mod={{ rotated: isExpanded }} />
        </Button>
      </Elem>

      {isExpanded && (
        <Elem name="content">
          <Elem name="workspaces-grid">
            {workspaces.map((workspace) => (
              <WorkspaceCard key={workspace.id} workspace={workspace} onUpdate={onUpdate} currentUser={currentUser} />
            ))}
          </Elem>
        </Elem>
      )}
    </Block>
  );
};
