import React, { useEffect, useState } from 'react';
import { Select } from '@humansignal/ui';
import { useAPI } from '../../providers/ApiProvider';
import { Caption } from '../../components/Caption/Caption';

const WorkspaceSelector = ({ value, onChange, disabled }) => {
  const [workspaces, setWorkspaces] = useState([]);
  const [loading, setLoading] = useState(true);
  const api = useAPI();

  useEffect(() => {
    const fetchWorkspaces = async () => {
      try {
        setLoading(true);
        const response = await api.callApi('workspaces');
        setWorkspaces(response || []);
      } catch (error) {
        console.error('Failed to fetch workspaces:', error);
        setWorkspaces([]);
      } finally {
        setLoading(false);
      }
    };

    fetchWorkspaces();
  }, [api]);

  const options = [
    { value: '', label: 'No workspace' },
    ...workspaces.map(workspace => ({
      value: workspace.id,
      label: workspace.name
    }))
  ];

  return (
    <div className="w-full flex flex-col gap-2">
      <label htmlFor="workspace_select">
        Workspace
      </label>
      <Select
        id="workspace_select"
        placeholder={loading ? "Loading workspaces..." : "Select a workspace"}
        disabled={disabled || loading}
        options={options}
        value={value}
        onChange={onChange}
        className="!flex-1"
      />
      <Caption>
        Organize your projects by grouping them into workspaces.{" "}
        {workspaces.length === 0 && !loading && (
          <span>
            <a href="/workspaces">Create a workspace</a> to get started.
          </span>
        )}
      </Caption>
    </div>
  );
};

export default WorkspaceSelector; 