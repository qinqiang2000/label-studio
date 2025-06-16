import React, { useEffect, useState, forwardRef } from 'react';
import { Select, Tooltip } from '@humansignal/ui';
import { useAPI } from '../../providers/ApiProvider';
import { FormField } from '../../components/Form/FormField';

const WorkspaceSelector = forwardRef(({ value, onChange, disabled, showLabel = false, children, name, validate, required, skip, ...props }, ref) => {
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

  // If used as children for another Select component
  if (children !== undefined) {
    return (
      <>
        <Select.Option value="">Select an option</Select.Option>
        {workspaces.map(workspace => (
          <Select.Option key={workspace.id} value={workspace.id}>
            {workspace.name}
          </Select.Option>
        ))}
      </>
    );
  }

  const options = [
    { value: '', label: <Tooltip title="[Notice] This project will be visible to all users in the organization!"><span>No workspace (visible to all users!)</span></Tooltip> },
    ...workspaces.map(workspace => ({
      value: workspace.id,
      label: workspace.name
    }))
  ];

  // If this component has a name prop, it should be integrated with Form
  if (name) {
    return (
      <FormField
        name={name}
        validate={validate}
        required={required}
        skip={skip}
        {...props}
      >
        {(fieldRef) => (
          <Select
            ref={fieldRef}
            placeholder={loading ? "Loading workspaces..." : "Select a workspace"}
            disabled={disabled || loading}
            options={options}
            value={value}
            onChange={onChange}
            {...props}
          />
        )}
      </FormField>
    );
  }

  // Standalone component
  return (
    <Select
      ref={ref}
      placeholder={loading ? "Loading workspaces..." : "Select a workspace"}
      disabled={disabled || loading}
      options={options}
      value={value}
      onChange={onChange}
      {...props}
    />
  );
});

export default WorkspaceSelector; 