import React, { useCallback } from 'react';
import { Block, Elem } from '../../utils/bem';
import { Button } from '@humansignal/ui';
import { IconChevron, IconGear, IconEllipsisVertical } from '@humansignal/icons';
import { useAPI } from '../../providers/ApiProvider';
import { modal } from '../../components/Modal/Modal';
import { Dropdown } from '../../components/Dropdown/Dropdown';
import { Menu } from '../../components/Menu/Menu';
import { EditWorkspaceModal } from './EditWorkspaceModal';
import { ManageMembersModal } from './ManageMembersModal';
import { timeAgo } from '../../utils/helpers';
import './WorkspaceCard.scss';

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

interface WorkspaceCardProps {
  workspace: Workspace;
  onUpdate: () => void;
  currentUser?: {
    is_superuser?: boolean;
  };
}

export const WorkspaceCard: React.FC<WorkspaceCardProps> = ({ workspace, onUpdate, currentUser }) => {
  const api = useAPI();
  const isAdmin = currentUser?.is_superuser || false;

  const handleEditWorkspace = useCallback(() => {
    const modalInstance = modal({
      title: 'Edit Workspace',
      body: (
        <EditWorkspaceModal
          workspace={workspace}
          onClose={() => modalInstance.close()}
          onWorkspaceUpdated={() => {
            onUpdate();
            modalInstance.close();
          }}
        />
      ),
      style: { width: 600 }
    });
  }, [workspace, onUpdate]);

  const handleManageMembers = useCallback(() => {
    const modalInstance = modal({
      title: 'Manage Members',
      body: (
        <ManageMembersModal
          workspace={workspace}
          onClose={() => modalInstance.close()}
          onMembersUpdated={() => {
            onUpdate();
            modalInstance.close();
          }}
        />
      ),
      style: { width: 800 }
    });
  }, [workspace, onUpdate]);

  const handleArchiveWorkspace = useCallback(async () => {
    const action = workspace.is_archived ? 'unarchive' : 'archive';
    const confirmed = confirm(`Are you sure you want to ${action} this workspace?`);
    
    if (!confirmed) return;

    try {
      await api.callApi('archiveWorkspace', {
        params: { pk: workspace.id }
      });
      onUpdate();
    } catch (error) {
      console.error(`Failed to ${action} workspace:`, error);
      alert(`Failed to ${action} workspace. Please try again.`);
    }
  }, [workspace, api, onUpdate]);

  const handleDeleteWorkspace = useCallback(async () => {
    const confirmed = confirm('Are you sure you want to delete this workspace? This action cannot be undone.');
    
    if (!confirmed) return;

    try {
      await api.callApi('deleteWorkspace', {
        params: { pk: workspace.id }
      });
      onUpdate();
    } catch (error) {
      console.error('Failed to delete workspace:', error);
      alert('Failed to delete workspace. Please try again.');
    }
  }, [workspace, api, onUpdate]);

  const handleViewProjects = useCallback(() => {
    // Navigate to projects filtered by workspace
    window.location.href = `/projects?workspace=${workspace.id}`;
  }, [workspace.id]);

  return (
    <Block name="workspace-card">
      <Elem name="header">
        <Elem name="color-indicator" style={{ backgroundColor: workspace.color }} />
        <Elem name="info">
          <Elem name="title">{workspace.name}</Elem>
          <Elem name="description">{workspace.description || 'No description'}</Elem>
        </Elem>
        {isAdmin && (
          <Elem name="actions">
            <Dropdown.Trigger content={
              <Menu>
                <Menu.Item onClick={handleEditWorkspace}>Edit</Menu.Item>
                <Menu.Item onClick={handleManageMembers}>Manage Members</Menu.Item>
                <Menu.Divider />
                <Menu.Item onClick={handleArchiveWorkspace}>
                  {workspace.is_archived ? 'Unarchive' : 'Archive'}
                </Menu.Item>
                <Menu.Item onClick={handleDeleteWorkspace}>Delete</Menu.Item>
              </Menu>
            }>
              <Button type="link" icon={<IconEllipsisVertical />} size="small" />
            </Dropdown.Trigger>
          </Elem>
        )}
      </Elem>
      
      <Elem name="stats">
        <Elem name="stat">
          <Elem name="stat-value">{workspace.member_count}</Elem>
          <Elem name="stat-label">Members</Elem>
        </Elem>
        <Elem name="stat">
          <Elem name="stat-value">{workspace.project_count}</Elem>
          <Elem name="stat-label">Projects</Elem>
        </Elem>
      </Elem>

      <Elem name="footer">
        <Button
          look="alt"
          size="small"
          onClick={handleViewProjects}
        >
          View Projects <IconChevron />
        </Button>
        <Elem name="created-info">
          Created {timeAgo(workspace.created_at)} by {workspace.created_by.email}
        </Elem>
      </Elem>
    </Block>
  );
}; 