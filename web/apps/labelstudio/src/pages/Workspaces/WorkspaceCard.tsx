import React, { useCallback, useState } from 'react';
import { Block, Elem } from '../../utils/bem';
import { Button } from '@humansignal/ui';
import { IconChevron, IconGear, IconEllipsisVertical, IconChevronDown, IconChevronRight } from '@humansignal/icons';
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

interface Project {
  id: number;
  title: string;
  description: string;
  color: string;
  task_number: number;
  created_at: string;
}

interface Prompt {
  id: number;
  name: string;
  content_preview: string;
  temperature: number | null;
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
  const [showProjects, setShowProjects] = useState(false);
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectsLoading, setProjectsLoading] = useState(false);
  const [showPrompts, setShowPrompts] = useState(false);
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [promptsLoading, setPromptsLoading] = useState(false);

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
            // Don't close modal to allow multiple operations
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
      const response = await api.callApi('archiveWorkspace', {
        params: { pk: workspace.id }
      });
      
      onUpdate();
    } catch (error: any) {
      console.error(`Failed to ${action} workspace:`, error);
      
      // Show specific error message if available
      const errorMessage = error?.response?.data?.error || `Failed to ${action} workspace. Please try again.`;
      alert(errorMessage);
    }
  }, [workspace, api, onUpdate]);

  const handleDeleteWorkspace = useCallback(async () => {
    const confirmed = confirm('Are you sure you want to delete this workspace? This action cannot be undone.');
    
    if (!confirmed) return;

    const result = await api.callApi('deleteWorkspace', {
      params: { pk: workspace.id },
      suppressError: true
    });
    
    if (result?.error) {
      console.error('Failed to delete workspace:', result);
      
      // Show specific error message if available, otherwise show a generic message
      let errorMessage = 'Failed to delete workspace. Please try again.';
      
      if (result?.response?.error) {
        // If it's the specific error about projects, show a more user-friendly message
        const serverError = result.response.error;
        if (serverError.includes('project(s)')) {
          errorMessage = 'If you want to delete a workspace, first delete the projects or move them to another workspace from the project settings.';
        } else {
          errorMessage = serverError;
        }
      }
      
      alert(errorMessage);
    } else {
      // Success - update the workspace list
      onUpdate();
    }
  }, [workspace, api, onUpdate]);

  const handleToggleProjects = useCallback(async () => {
    if (!showProjects && projects.length === 0) {
      // Fetch projects if not already loaded
      try {
        setProjectsLoading(true);
        const response = await api.callApi('workspaceProjects', {
          params: { pk: workspace.id }
        });
        setProjects((response as unknown as Project[]) || []);
      } catch (error) {
        console.error('Failed to fetch workspace projects:', error);
        alert('Failed to load projects. Please try again.');
        return;
      } finally {
        setProjectsLoading(false);
      }
    }
    setShowProjects(!showProjects);
  }, [showProjects, projects.length, workspace.id, api]);

  const handleTogglePrompts = useCallback(async () => {
    if (!showPrompts && prompts.length === 0) {
      // Fetch prompts if not already loaded
      try {
        setPromptsLoading(true);
        const response = await api.callApi('workspacePrompts', {
          params: { pk: workspace.id }
        });
        setPrompts((response as unknown as Prompt[]) || []);
      } catch (error) {
        console.error('Failed to fetch workspace prompts:', error);
        alert('Failed to load prompts. Please try again.');
        return;
      } finally {
        setPromptsLoading(false);
      }
    }
    setShowPrompts(!showPrompts);
  }, [showPrompts, prompts.length, workspace.id, api]);

  const handleViewProject = useCallback((projectId: number) => {
    window.location.href = `/projects/${projectId}`;
  }, []);

  const handleViewPrompt = useCallback((promptId: number) => {
    window.location.href = `/prompts#${promptId}`;
  }, []);

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
        <Elem name="stat">
          <Elem name="stat-value">{workspace.prompt_count}</Elem>
          <Elem name="stat-label">Prompts</Elem>
        </Elem>
      </Elem>

      <Elem name="footer">
        <Elem name="footer-buttons">
          <Button
            look="alt"
            size="small"
            onClick={handleToggleProjects}
            disabled={projectsLoading}
            icon={showProjects ? <IconChevronDown /> : <IconChevronRight />}
          >
            {projectsLoading ? 'Loading...' : showProjects ? 'Hide Projects' : 'Show Projects'}
          </Button>
          <Button
            look="alt"
            size="small"
            onClick={handleTogglePrompts}
            disabled={promptsLoading}
            icon={showPrompts ? <IconChevronDown /> : <IconChevronRight />}
          >
            {promptsLoading ? 'Loading...' : showPrompts ? 'Hide Prompts' : 'Show Prompts'}
          </Button>
        </Elem>
      </Elem>

      {showProjects && (
        <Elem name="projects-list">
          {projects.length === 0 ? (
            <Elem name="no-projects">No projects in this workspace yet</Elem>
          ) : (
            projects.map((project) => (
              <Elem 
                key={project.id} 
                name="project-item"
                onClick={() => handleViewProject(project.id)}
              >
                <Elem name="project-color" style={{ backgroundColor: project.color }} />
                <Elem name="project-info">
                  <Elem name="project-title">{project.title}</Elem>
                  <Elem name="project-description">
                    {project.description || 'No description'} • {project.task_number} tasks
                  </Elem>
                </Elem>
                <Elem name="project-created">
                  {timeAgo(project.created_at)}
                </Elem>
              </Elem>
            ))
          )}
        </Elem>
      )}

      {showPrompts && (
        <Elem name="prompts-list">
          {prompts.length === 0 ? (
            <Elem name="no-prompts">No prompts in this workspace yet</Elem>
          ) : (
            prompts.map((prompt) => (
              <Elem 
                key={prompt.id} 
                name="prompt-item"
                onClick={() => handleViewPrompt(prompt.id)}
              >
                <Elem name="prompt-info">
                  <Elem name="prompt-title">{prompt.name}</Elem>
                  <Elem name="prompt-description">
                    {prompt.temperature !== null && prompt.temperature !== undefined && (
                      <span style={{ color: '#666' }}>
                        Temperature: {prompt.temperature}
                      </span>
                    )}
                  </Elem>
                </Elem>
                <Elem name="prompt-created">
                  {timeAgo(prompt.created_at)}
                </Elem>
              </Elem>
            ))
          )}
        </Elem>
      )}
    </Block>
  );
};