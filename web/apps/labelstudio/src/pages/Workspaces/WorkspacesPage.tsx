import React, { useCallback, useEffect, useState } from 'react';
import { Button } from '@humansignal/ui';
import { Block, Elem } from '../../utils/bem';
import { useAPI } from '../../providers/ApiProvider';
import { modal } from '../../components/Modal/Modal';
import { CreateWorkspaceModal } from './CreateWorkspaceModal';
import { WorkspaceCard } from './WorkspaceCard';
import { WorkspaceArchived } from './WorkspaceArchived';
import { useButtonPermissions } from '../../hooks/useButtonPermissions';
import { SmartButton } from '../../components/SmartPermission/SmartButton';
import './WorkspacesPage.scss';

interface Workspace {
  id: number;
  name: string;
  description: string;
  color: string;
  is_archived: boolean;
  member_count: number;
  project_count: number;
  prompt_count: number;
  created_by: {
    id: number;
    email: string;
    first_name: string;
    last_name: string;
  };
  created_at: string;
  updated_at: string;
}

interface User {
  id: string;
  email: string;
  is_superuser: boolean;
}

export const WorkspacesPage: React.FC = () => {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [archivedWorkspaces, setArchivedWorkspaces] = useState<Workspace[]>([]);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [showArchived, setShowArchived] = useState(false);
  
  const api = useAPI();
  const buttonPermissions = useButtonPermissions();

  const fetchCurrentUser = useCallback(async () => {
    try {
      const user = await api.callApi('currentUser');
      setCurrentUser(user);
    } catch (error) {
      console.error('Failed to fetch current user:', error);
    }
  }, [api]);

  const fetchWorkspaces = useCallback(async () => {
    try {
      setLoading(true);
      // Fetch active workspaces
      const response = await api.callApi('workspaces');
      setWorkspaces(response || []);
      
      // Fetch archived workspaces
      const archivedResponse = await api.callApi('archivedWorkspaces');
      setArchivedWorkspaces(archivedResponse || []);
    } catch (error) {
      console.error('Failed to fetch workspaces:', error);
      setWorkspaces([]);
      setArchivedWorkspaces([]);
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => {
    fetchCurrentUser();
    fetchWorkspaces();
  }, [fetchCurrentUser, fetchWorkspaces]);

  const handleCreateWorkspace = useCallback(() => {
    const modalInstance = modal({
      title: 'Create Workspace',
      body: (
        <CreateWorkspaceModal
          onClose={() => modalInstance.close()}
          onWorkspaceCreated={() => {
            fetchWorkspaces();
            modalInstance.close();
          }}
        />
      ),
      style: { width: 600 }
    });
  }, [fetchWorkspaces]);

  const handleWorkspaceUpdate = useCallback(() => {
    fetchWorkspaces();
  }, [fetchWorkspaces]);

  if (loading) {
    return (
      <Block name="workspaces-page">
        <Elem name="loading">Loading workspaces...</Elem>
      </Block>
    );
  }

  // Check permissions for workspace operations
  const canCreateWorkspace = buttonPermissions.createWorkspace;

  return (
    <Block name="workspaces-page">
      <Elem name="header">
        <Elem name="title">
          <h1>Workspaces</h1>
          <Elem name="subtitle">
            Organize and manage your projects by grouping them into workspaces
          </Elem>
        </Elem>
        <Elem name="actions">
          <SmartButton
            permission="show_create_workspace_button"
            onClick={handleCreateWorkspace}
            look="primary"
            fallback="hide"
          >
            Create Workspace
          </SmartButton>
        </Elem>
      </Elem>

      <Elem name="content">
        {workspaces.length === 0 && archivedWorkspaces.length === 0 ? (
          <Elem name="empty-state">
            <Elem name="empty-icon">🏢</Elem>
            <Elem name="empty-title">No workspaces yet</Elem>
            <Elem name="empty-description">
              {canCreateWorkspace 
                ? "Create your first workspace to organize your projects"
                : "No workspaces available. Contact an administrator to create workspaces."
              }
            </Elem>
            <SmartButton
              permission="show_create_workspace_button"
              onClick={handleCreateWorkspace}
              look="primary"
              size="large"
              fallback="hide"
            >
              Create Workspace
            </SmartButton>
          </Elem>
        ) : (
          <>
            {workspaces.length > 0 && (
              <Elem name="workspaces-grid">
                {workspaces.map((workspace) => (
                  <WorkspaceCard
                    key={workspace.id}
                    workspace={workspace}
                    onUpdate={handleWorkspaceUpdate}
                    currentUser={currentUser}
                  />
                ))}
              </Elem>
            )}

            {archivedWorkspaces.length > 0 && (
              <WorkspaceArchived
                workspaces={archivedWorkspaces}
                isExpanded={showArchived}
                onToggle={() => setShowArchived(!showArchived)}
                onUpdate={handleWorkspaceUpdate}
                currentUser={currentUser}
              />
            )}
          </>
        )}
      </Elem>
    </Block>
  );
}; 