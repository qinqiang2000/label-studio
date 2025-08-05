import { useEffect, useState, forwardRef } from "react";
import { Select, Tooltip } from "@humansignal/ui";
import { useAPI } from "../../providers/ApiProvider";
import { FormField } from "../../components/Form/FormField";

const WorkspaceSelector = forwardRef(
  (
    {
      value,
      onChange,
      disabled,
      showLabel = false,
      children,
      name,
      validate,
      required,
      skip,
      multiple = false,
      ...props
    },
    ref,
  ) => {
    const [workspaces, setWorkspaces] = useState([]);
    const [loading, setLoading] = useState(true);
    const api = useAPI();

    useEffect(() => {
      const fetchWorkspaces = async () => {
        try {
          setLoading(true);
          const response = await api.callApi("workspaces");
          setWorkspaces(response || []);
        } catch (error) {
          console.error("Failed to fetch workspaces:", error);
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
          {workspaces.map((workspace) => (
            <Select.Option key={workspace.id} value={workspace.id}>
              {workspace.name}
            </Select.Option>
          ))}
        </>
      );
    }

    const options = multiple
      ? [
          // For multiple selection, don't include the "No workspace" option as a selectable item
          // Instead, empty selection means no workspaces (organization-wide)
          ...workspaces.map((workspace) => ({
            value: workspace.id,
            label: workspace.name,
          })),
        ]
      : [
          {
            value: "",
            label: (
              <Tooltip title="[Notice] This project will be visible to all users in the organization!">
                <span>No workspace (visible to all users!)</span>
              </Tooltip>
            ),
          },
          ...workspaces.map((workspace) => ({
            value: workspace.id,
            label: workspace.name,
          })),
        ];

    // Get the placeholder text based on current state
    const getPlaceholder = () => {
      if (loading) return "Loading workspaces...";

      if (multiple) {
        if (Array.isArray(value) && value.length > 0) {
          if (value.length === 1) {
            const selectedWorkspace = workspaces.find((w) => w.id === value[0]);
            return selectedWorkspace ? selectedWorkspace.name : `Workspace #${value[0]}`;
          }
          return `${value.length} workspaces selected`;
        }
        return props.placeholder || "Select workspaces (organization-wide if none selected)";
      } else {
        if (value && value !== "") {
          // Find the workspace name for the current value
          const selectedWorkspace = workspaces.find((w) => w.id === value);
          if (selectedWorkspace) {
            return selectedWorkspace.name;
          }
          // If value is set but workspace not found, show the ID
          return `Workspace #${value}`;
        }
        return props.placeholder || "Select a workspace (optional)";
      }
    };

    // If this component has a name prop, it should be integrated with Form
    if (name) {
      return (
        <FormField name={name} validate={validate} required={required} skip={skip} {...props}>
          {(fieldRef) => (
            <Select
              ref={fieldRef}
              placeholder={getPlaceholder()}
              disabled={disabled || loading}
              options={options}
              value={value}
              onChange={onChange}
              multiple={multiple}
              getPopupContainer={props.getPopupContainer || ((trigger) => trigger.parentNode)}
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
        placeholder={getPlaceholder()}
        disabled={disabled || loading}
        options={options}
        value={value}
        onChange={onChange}
        multiple={multiple}
        getPopupContainer={props.getPopupContainer || ((trigger) => trigger.parentNode)}
        {...props}
      />
    );
  },
);

export default WorkspaceSelector;
