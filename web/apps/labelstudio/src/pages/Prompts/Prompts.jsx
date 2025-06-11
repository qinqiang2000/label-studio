import React, { useState, useEffect, useCallback } from "react";
import { Button } from "../../components";
import { Spinner } from "../../components/Spinner/Spinner";
import { modal } from "../../components/Modal/Modal";
import { cn } from "../../utils/bem";
import { useAPI } from "../../providers/ApiProvider";
import { useCurrentUser } from "../../providers/CurrentUser";
import "./Prompts.scss";

const Block = cn("prompts-page");

const PromptForm = ({ prompt, onSave, onCancel, isLoading }) => {
  const [formData, setFormData] = useState({
    name: prompt?.name || "",
    content: prompt?.content || "",
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    console.log("=== FORM SUBMIT DEBUG ===");
    console.log("Form data being submitted:", formData);
    console.log("onSave function:", onSave);
    onSave(formData);
  };

  const handleChange = (field) => (e) => {
    setFormData(prev => ({
      ...prev,
      [field]: e.target.value
    }));
  };

  const handleCancel = (e) => {
    e.preventDefault();
    if (onCancel && typeof onCancel === 'function') {
      onCancel();
    }
  };

  return (
    <form onSubmit={handleSubmit} className={Block.elem("form")}>
      <div className={Block.elem("form-field")}>
        <label htmlFor="name">Name</label>
        <input
          id="name"
          type="text"
          value={formData.name}
          onChange={handleChange("name")}
          required
          disabled={isLoading}
          placeholder="Enter prompt name"
        />
      </div>
      
      <div className={Block.elem("form-field")}>
        <label htmlFor="content">Prompt</label>
        <textarea
          id="content"
          value={formData.content}
          onChange={handleChange("content")}
          rows="12"
          required
          disabled={isLoading}
          placeholder="Enter your prompt content here..."
        />
      </div>
      
      <div className={Block.elem("form-actions")}>
        <Button type="button" onClick={handleCancel} disabled={isLoading}>
          Cancel
        </Button>
        <Button type="submit" look="primary" disabled={isLoading}>
          {isLoading ? "Saving..." : "Save"}
        </Button>
      </div>
    </form>
  );
};

const PromptCard = ({ prompt, onEdit, onDelete }) => {
  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hour = String(date.getHours()).padStart(2, '0');
    const minute = String(date.getMinutes()).padStart(2, '0');
    return `${year}-${month}-${day} ${hour}:${minute}`;
  };

  const handleCardClick = (e) => {
    // 如果点击的是按钮，不触发卡片点击事件
    if (e.target.closest('button')) {
      return;
    }
    onEdit(prompt);
  };

  const handleEditClick = (e) => {
    e.stopPropagation();
    onEdit(prompt);
  };

  const handleDeleteClick = (e) => {
    e.stopPropagation();
    onDelete(prompt);
  };

  return (
    <div className={Block.elem("card")} onClick={handleCardClick}>
      <div className={Block.elem("card-header")}>
        <h3 className={Block.elem("card-title")}>{prompt.name}</h3>
        <div className={Block.elem("card-actions")}>
          <Button size="compact" onClick={handleEditClick}>
            Edit
          </Button>
          <Button size="compact" look="destructive" onClick={handleDeleteClick}>
            Delete
          </Button>
        </div>
      </div>
      
      <div className={Block.elem("card-content")}>
        <pre className={Block.elem("card-prompt")}>{prompt.content}</pre>
      </div>
      
      <div className={Block.elem("card-footer")}>
        <small>Updated: {formatDate(prompt.updated_at)}</small>
      </div>
    </div>
  );
};

export const PromptsPage = () => {
  const api = useAPI();
  const { user } = useCurrentUser();
  const [prompts, setPrompts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentModal, setCurrentModal] = useState(null);
  const [editingPrompt, setEditingPrompt] = useState(null);
  const [saving, setSaving] = useState(false);

  const loadPrompts = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.callApi("getPrompts");
      // Label Studio API直接返回数据，不是包装在data字段中
      if (Array.isArray(response)) {
        setPrompts(response);
      } else {
        setPrompts([]);
      }
    } catch (error) {
      console.error("Failed to load prompts:", error);
      setPrompts([]);
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => {
    loadPrompts();
  }, [loadPrompts]);

  const handleCreatePrompt = () => {
    openModal();
  };

  const handleEditPrompt = (prompt) => {
    openModal(prompt);
  };

  const openModal = (promptToEdit = null) => {
    console.log("=== MODAL DEBUG START ===");
    console.log("promptToEdit:", promptToEdit);
    console.log("Setting editingPrompt to:", promptToEdit);
    
    // 重要：使用useEffect或者setTimeout来确保状态更新后再创建模态框
    setTimeout(() => {
      console.log("Creating modal after state update");
      
      let modalInstance; // 声明在外层作用域
      
      const closeModalHandler = () => {
        console.log("closeModalHandler called");
        if (modalInstance && typeof modalInstance.close === 'function') {
          try {
            console.log("Closing modal instance with close() method");
            modalInstance.close();
          } catch (error) {
            console.warn('Error closing modal:', error);
          }
        } else if (modalInstance && typeof modalInstance.hide === 'function') {
          try {
            console.log("Hiding modal instance with hide() method");
            modalInstance.hide();
          } catch (error) {
            console.warn('Error hiding modal:', error);
          }
        } else {
          console.warn('Modal instance has no close or hide method:', modalInstance);
        }
        console.log("Clearing current modal and editing prompt");
        setCurrentModal(null);
        setEditingPrompt(null);
      };
      
      modalInstance = modal({
        title: promptToEdit ? "Edit Prompt" : "Create Prompt",
        style: {
          width: '80vw',
          maxWidth: '1000px',
          height: '70vh',
          maxHeight: '700px'
        },
        body: () => (
          <PromptForm
            prompt={promptToEdit}
            onSave={(formData) => handleSavePrompt(formData, closeModalHandler, promptToEdit)}
            onCancel={closeModalHandler}
            isLoading={saving}
          />
        ),
        onHide: () => {
          setCurrentModal(null);
          setEditingPrompt(null);
        },
      });
      setCurrentModal(modalInstance);
    }, 0);
    
    setEditingPrompt(promptToEdit); // 设置编辑状态
  };

  const closeModal = () => {
    if (currentModal && typeof currentModal.close === 'function') {
      try {
        currentModal.close();
      } catch (error) {
        console.warn('Error closing modal:', error);
      }
    } else if (currentModal && typeof currentModal.hide === 'function') {
      try {
        currentModal.hide();
      } catch (error) {
        console.warn('Error hiding modal:', error);
      }
    }
    setCurrentModal(null);
    setEditingPrompt(null);
  };

  const handleSavePrompt = async (formData, closeHandler, promptToEdit = null) => {
    console.log("=== SAVE DEBUG START ===");
    console.log("formData:", formData);
    console.log("promptToEdit param:", promptToEdit);
    console.log("editingPrompt state:", editingPrompt);
    console.log("closeHandler type:", typeof closeHandler);
    
    // 使用传入的promptToEdit参数而不是状态，因为状态可能还没更新
    const isEditing = promptToEdit !== null;
    
    try {
      setSaving(true);
      console.log("Setting saving to true");
      
      if (isEditing) {
        console.log("UPDATING existing prompt with ID:", promptToEdit.id);
        // Update existing prompt
        const response = await api.callApi("updatePrompt", {
          params: { id: promptToEdit.id },
          body: formData,
        });
        console.log("Prompt updated successfully:", response);
      } else {
        console.log("CREATING new prompt");
        // Create new prompt
        const response = await api.callApi("createPrompt", {
          body: formData,
        });
        console.log("Prompt created successfully:", response);
      }
      
      console.log("About to close modal");
      // 先关闭模态框，再重新加载数据
      if (closeHandler && typeof closeHandler === 'function') {
        console.log("Calling closeHandler");
        closeHandler();
      } else {
        console.log("closeHandler is not a function or is null");
      }
      
      console.log("About to reload prompts");
      // 重新加载prompts
      await loadPrompts();
      console.log("Prompts reloaded");
      
    } catch (error) {
      console.error("Failed to save prompt:", error);
      console.error("Error response:", error.response);
      console.error("Error response data:", error.response?.data);
      
      // 显示错误信息给用户
      let errorMessage = "Failed to save prompt. Please try again.";
      
      if (error.response?.data) {
        const errorData = error.response.data;
        if (errorData.name && Array.isArray(errorData.name)) {
          errorMessage = `Error: ${errorData.name[0]}`;
        } else if (errorData.name) {
          errorMessage = `Error: ${errorData.name}`;
        } else if (typeof errorData === 'string') {
          errorMessage = `Error: ${errorData}`;
        }
      }
      
      alert(errorMessage);
    } finally {
      console.log("Setting saving to false");
      setSaving(false);
      console.log("=== SAVE DEBUG END ===");
    }
  };

  const handleDeletePrompt = async (prompt) => {
    if (window.confirm(`Are you sure you want to delete "${prompt.name}"?`)) {
      try {
        await api.callApi("deletePrompt", {
          params: { id: prompt.id },
        });
        await loadPrompts();
      } catch (error) {
        console.error("Failed to delete prompt:", error);
      }
    }
  };



  if (loading) {
    return (
      <div className={Block}>
        <div className={Block.elem("loading")}>
          <Spinner size={64} />
        </div>
      </div>
    );
  }

  return (
    <div className={Block}>
      <div className={Block.elem("header")}>
        <h1 className={Block.elem("title")}>Prompts</h1>
        <Button onClick={handleCreatePrompt} look="primary">
          Create Prompt
        </Button>
      </div>

      <div className={Block.elem("content")}>
        {prompts.length === 0 ? (
          <div className={Block.elem("empty")}>
            <h2>No prompts yet</h2>
            <p>Create your first prompt to get started.</p>
            <Button onClick={handleCreatePrompt} look="primary">
              Create Prompt
            </Button>
          </div>
        ) : (
          <div 
            className={Block.elem("grid")} 
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))',
              gap: '20px'
            }}
          >
            {prompts.map(prompt => (
              <PromptCard
                key={prompt.id}
                prompt={prompt}
                onEdit={handleEditPrompt}
                onDelete={handleDeletePrompt}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

PromptsPage.title = "Prompts";
PromptsPage.path = "/prompts";
PromptsPage.exact = true;