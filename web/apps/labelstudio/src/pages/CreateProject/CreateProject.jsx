import { Select } from "@humansignal/ui";
import React from "react";
import { useHistory } from "react-router";
import { Button, ToggleItems } from "../../components";
import { Modal } from "../../components/Modal/Modal";
import { Space } from "../../components/Space/Space";
import { useAPI } from "../../providers/ApiProvider";
import { Block, Elem } from "../../utils/bem";
import { cn } from "../../utils/bem";
import { ConfigPage } from "./Config/Config";
import "./CreateProject.scss";
import { ImportPage } from "./Import/Import";
import { useImportPage } from "./Import/useImportPage";
import { useDraftProject } from "./utils/useDraftProject";
import { Input, TextArea } from "../../components/Form";
import { Caption } from "../../components/Caption/Caption";
import WorkspaceSelector from "./WorkspaceSelector";

// Dynamic document type configurations - loaded from API
// Fallback configurations for development/testing
const FALLBACK_DOCUMENT_TYPE_CONFIGS = {
  invoice: {
    label: "Invoice",
    fields: ["totalAmount", "invoiceDate", "docType", "currency", "billToName", "totalTaxAmount"],
    description: "For evaluating invoices and receipts",
  },
  bank_receipt: {
    label: "Bank Receipt",
    fields: [
      "tradeId",
      "recieptNum",
      "logNum",
      "tradeDate",
      "amount",
      "paymentName",
      "paymentBank",
      "paymentAccount",
      "payeeName",
      "payeeBank",
      "payeeAccount",
      "currency",
    ],
    description: "For evaluating bank receipts",
  },
};

const ProjectName = ({
  name,
  setName,
  onSaveName,
  onSubmit,
  error,
  description,
  setDescription,
  workspace,
  setWorkspace,
  evaluationConfig,
  setEvaluationConfig,
  evaluationConfigs = [],
  isLoadingConfigs = false,
  show = true,
}) => {
  if (!show) return null;

  return (
    <form
      className={cn("project-name")}
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
    >
      {/* Project title */}
      <div className="w-full flex flex-col gap-2">
        <label className="w-full" htmlFor="project_name">
          Project Name
        </label>
        <Input
          name="name"
          id="project_name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          onBlur={onSaveName}
          className="project-title w-full"
        />
        {error && <span className="-mt-1 text-negative-content">{error}</span>}
      </div>

      {/* Description */}
      <div className="w-full flex flex-col gap-2">
        <label className="w-full" htmlFor="project_description">
          Description
        </label>
        <TextArea
          name="description"
          id="project_description"
          placeholder="Optional description of your project"
          rows={4}
          style={{ minHeight: 100 }}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="project-description w-full"
        />
      </div>

      {/* Workspace selector */}
      {/* <div className="w-full flex flex-col gap-2"> */}
      <Block name="workspace-section">
        <Elem name="badge-wrapper">
          <Elem name="title">Workspace</Elem>
        </Elem>
        <WorkspaceSelector value={workspace || ""} onChange={(value) => setWorkspace(value || null)} />
        <Caption>Organize your projects by grouping them into workspaces.</Caption>
      </Block>
      {/* </div> */}

      {/* Evaluation Configuration */}
      <div className="gap-2">
        <label className="w-full" htmlFor="evaluation_config">
          Evaluation Field Configuration
        </label>
        <Select
          id="evaluation_config"
          value={evaluationConfig}
          onChange={setEvaluationConfig}
          options={evaluationConfigs.map((config) => ({
            value: config.value,
            label: config.label,
          }))}
          placeholder={isLoadingConfigs ? "Loading configurations..." : "Select Evaluation Configuration"}
          disabled={isLoadingConfigs}
          className="evaluation-config-select"
        />
        <Caption>
          {(() => {
            const selectedConfig = evaluationConfigs.find((config) => config.value === evaluationConfig);
            return selectedConfig?.description || "Select a configuration to see its description";
          })()}
          <br />
          To customize evaluation fields, configure them in Project Settings &gt; General Settings after project
          creation.
        </Caption>
      </div>

      <Button type="submit" look="primary" className="w-full mt-8">
        Save Project
      </Button>
    </form>
  );
};

export const CreateProject = ({ onClose }) => {
  const [step, _setStep] = React.useState("name"); // name | import | config
  const [waiting, setWaitingStatus] = React.useState(false);

  const { project, setProject: updateProject } = useDraftProject();
  const history = useHistory();
  const api = useAPI();

  const [name, setName] = React.useState("");
  const [error, setError] = React.useState();
  const [description, setDescription] = React.useState("");
  const [sample, setSample] = React.useState(null);
  const [workspace, setWorkspace] = React.useState(null);
  const [evaluationConfig, setEvaluationConfig] = React.useState("");
  const [evaluationConfigs, setEvaluationConfigs] = React.useState([]);
  const [isLoadingConfigs, setIsLoadingConfigs] = React.useState(true);

  const setStep = React.useCallback((step) => {
    _setStep(step);
    const eventNameMap = {
      name: "project_name",
      import: "data_import",
      config: "labeling_setup",
    };
    __lsa(`create_project.tab.${eventNameMap[step]}`);
  }, []);

  React.useEffect(() => {
    setError(null);
  }, [name]);

  const { columns, uploading, uploadDisabled, finishUpload, pageProps, uploadSample } = useImportPage(project, sample);

  const rootClass = cn("create-project");
  const tabClass = rootClass.elem("tab");
  const steps = {
    name: <span className={tabClass.mod({ disabled: !!error })}>Project Name</span>,
    import: <span className={tabClass.mod({ disabled: uploadDisabled })}>Data Import</span>,
    config: "Labeling Setup",
  };

  // Load evaluation configurations from API
  React.useEffect(() => {
    const loadEvaluationConfigs = async () => {
      try {
        setIsLoadingConfigs(true);
        const response = await api.callApi("fetchEvaluationConfigs");
        if (response && Array.isArray(response)) {
          setEvaluationConfigs(response);
          // Set default selection to a suitable config - prefer Bank Receipt or Receipt over Invoice
          if (response.length > 0) {
            // Priority order: bank_receipt > receipt > invoice > first available
            const defaultConfig =
              response.find((config) => config.value === "invoice") ||
              response.find((config) => config.value === "bank_receipt") ||
              response.find((config) => config.value === "receipt") ||
              response[0];
            setEvaluationConfig(defaultConfig.value);
          }
        } else {
          // Fallback to hardcoded configs if API fails
          console.warn("Failed to load evaluation configs from API, using fallback");
          const fallbackConfigs = Object.entries(FALLBACK_DOCUMENT_TYPE_CONFIGS).map(([key, config]) => ({
            value: key,
            label: config.label,
            description: config.description,
            fields: config.fields,
            required_fields: config.fields,
            optional_fields: [],
          }));
          setEvaluationConfigs(fallbackConfigs);
        }
      } catch (error) {
        console.error("Error loading evaluation configs:", error);
        // Fallback to hardcoded configs
        const fallbackConfigs = Object.entries(FALLBACK_DOCUMENT_TYPE_CONFIGS).map(([key, config]) => ({
          value: key,
          label: config.label,
          description: config.description,
          fields: config.fields,
          required_fields: config.fields,
          optional_fields: [],
        }));
        setEvaluationConfigs(fallbackConfigs);
      } finally {
        setIsLoadingConfigs(false);
      }
    };

    loadEvaluationConfigs();
  }, [api]);

  // name intentionally skipped from deps:
  // this should trigger only once when we got project loaded
  React.useEffect(() => {
    project && !name && setName(project.title);
  }, [project]);

  const projectBody = React.useMemo(() => {
    const selectedConfig = evaluationConfigs.find((config) => config.value === evaluationConfig);
    return {
      title: name,
      description,
      workspace: workspace,
      label_config: project?.label_config ?? "<View></View>",
      evaluation_field_config: {
        document_type: evaluationConfig, // 后端API期望的字段名
        config_name: selectedConfig?.label || evaluationConfig,
        default_fields: selectedConfig?.fields || [],
        required_fields: selectedConfig?.required_fields || [],
        optional_fields: selectedConfig?.optional_fields || [],
        last_updated: new Date().toISOString(),
      },
    };
  }, [name, description, workspace, project?.label_config, evaluationConfig, evaluationConfigs]);

  const onCreate = React.useCallback(async () => {
    const imported = await finishUpload();

    if (!imported) return;

    setWaitingStatus(true);

    if (sample) await uploadSample(sample);

    __lsa("create_project.create", { sample: sample?.url });
    const response = await api.callApi("updateProject", {
      params: {
        pk: project.id,
      },
      body: projectBody,
    });

    setWaitingStatus(false);

    if (response !== null) {
      history.push(`/projects/${response.id}/data`);
    }
  }, [project, projectBody, finishUpload]);

  const onSaveName = async () => {
    if (error) return;
    const res = await api.callApi("updateProjectRaw", {
      params: {
        pk: project.id,
      },
      body: {
        title: name,
      },
    });

    if (res.ok) return;
    const err = await res.json();

    setError(err.validation_errors?.title);
  };

  const onDelete = React.useCallback(() => {
    const performClose = async () => {
      setWaitingStatus(true);
      if (project)
        await api.callApi("deleteProject", {
          params: {
            pk: project.id,
          },
        });
      setWaitingStatus(false);
      updateProject(null);
      onClose?.();
    };
    performClose();
  }, [project]);

  return (
    <Modal onHide={onDelete} closeOnClickOutside={false} allowToInterceptEscape fullscreen visible bare>
      <div className={rootClass}>
        <Modal.Header>
          <h1>Create Project</h1>
          <ToggleItems items={steps} active={step} onSelect={setStep} />

          <Space>
            <Button look="danger" size="compact" onClick={onDelete} waiting={waiting}>
              Delete
            </Button>
            <Button
              look="primary"
              size="compact"
              onClick={onCreate}
              waiting={waiting || uploading}
              disabled={!project || uploadDisabled || error}
            >
              Save
            </Button>
          </Space>
        </Modal.Header>
        <ProjectName
          name={name}
          setName={setName}
          error={error}
          onSaveName={onSaveName}
          onSubmit={onCreate}
          description={description}
          setDescription={setDescription}
          workspace={workspace}
          setWorkspace={setWorkspace}
          evaluationConfig={evaluationConfig}
          setEvaluationConfig={setEvaluationConfig}
          evaluationConfigs={evaluationConfigs}
          isLoadingConfigs={isLoadingConfigs}
          show={step === "name"}
        />
        <ImportPage
          project={project}
          show={step === "import"}
          sample={sample}
          onSampleDatasetSelect={setSample}
          openLabelingConfig={() => setStep("config")}
          {...pageProps}
        />
        <ConfigPage
          project={project}
          onUpdate={(config) => {
            updateProject({ ...project, label_config: config });
          }}
          show={step === "config"}
          columns={columns}
          disableSaveButton={true}
        />
      </div>
    </Modal>
  );
};
