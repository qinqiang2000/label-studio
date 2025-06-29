import React, { useCallback, useRef, useState, useEffect } from "react";
import { observer } from "mobx-react";
import { types } from "mobx-state-tree";

import Registry from "../../core/Registry";
import Tree from "../../core/Tree";
import Types from "../../core/Types";
import VisibilityMixin from "../../mixins/Visibility";
import { AnnotationMixin } from "../../mixins/AnnotationMixin";

// 用户偏好设置管理
const USER_PREFERENCE_KEY = 'ls_resizable_view_preferences';

const getUserPreferences = () => {
  try {
    const stored = localStorage.getItem(USER_PREFERENCE_KEY);
    return stored ? JSON.parse(stored) : {};
  } catch (error) {
    console.warn('Failed to load ResizableView user preferences:', error);
    return {};
  }
};

const saveUserPreference = (key, value) => {
  try {
    const preferences = getUserPreferences();
    preferences[key] = value;
    localStorage.setItem(USER_PREFERENCE_KEY, JSON.stringify(preferences));
  } catch (error) {
    console.warn('Failed to save ResizableView user preferences:', error);
  }
};

const getUserPreference = (key, defaultValue) => {
  const preferences = getUserPreferences();
  return preferences[key] !== undefined ? preferences[key] : defaultValue;
};

/**
 * The `ResizableView` element creates a resizable container with two panels that can be adjusted with a draggable separator.
 * @example
 * <ResizableView>
 *   <!-- Left panel -->
 *   <View>
 *     <HyperText name="pdf" value="$pdf" inline="true" height="100%" />
 *   </View>
 *   <!-- Right panel -->
 *   <View>
 *     <TextArea name="content" value="$content" rows="20" />
 *   </View>
 * </ResizableView>
 * @name ResizableView
 * @meta_title ResizableView Tag for Creating Resizable Split Panels
 * @meta_description Create resizable split panel layout in Label Studio for machine learning and data science projects.
 * @param {number} [leftMinWidth=300] - Minimum width for the left panel in pixels
 * @param {number} [rightMinWidth=250] - Minimum width for the right panel in pixels  
 * @param {number} [rightInitialWidth=350] - Initial width for the right panel in pixels
 * @param {string} [style] CSS style string
 */
const TagAttrs = types.model({
  leftminwidth: types.optional(types.string, "300"),
  rightminwidth: types.optional(types.string, "250"),
  rightinitialwidth: types.optional(types.string, "350"),
  style: types.maybeNull(types.string),
});

const Model = types
  .model({
    id: types.identifier,
    type: "resizableview",
    children: Types.unionArray([
      "view",
      "header",
      "labels",
      "label", 
      "text",
      "textarea",
      "hypertext",
      "image",
      "choices",
      "choice",
      "audio",
      "audioplus",
      "list",
      "dialog",
      "pairwise",
      "style",
      "relations",
      "filter",
      "pdf",
      "video"
    ]),
  })
  .views((self) => ({
    get isIndependent() {
      return true;
    },
  }));

const ResizableViewModel = types.compose("ResizableViewModel", TagAttrs, Model, VisibilityMixin, AnnotationMixin);

const HtxResizableView = observer(({ item }) => {
  const leftMinWidth = parseInt(item.leftminwidth) || 300;
  const rightMinWidth = parseInt(item.rightminwidth) || 250;
  const rightInitialWidth = parseInt(item.rightinitialwidth) || 350;
  
  // 生成唯一的偏好设置key，基于组件配置
  const preferenceKey = `rightPanelWidth_${leftMinWidth}_${rightMinWidth}_${rightInitialWidth}`;
  
  // 从用户偏好设置中获取保存的宽度，如果没有则使用默认值
  const savedWidth = getUserPreference(preferenceKey, rightInitialWidth);
  const [rightPanelWidth, setRightPanelWidth] = useState(savedWidth);
  const [isDragging, setIsDragging] = useState(false);
  const [isHovering, setIsHovering] = useState(false);
  const [isOptimized, setIsOptimized] = useState(false); // 性能优化模式
  const containerRef = useRef(null);
  const animationIdRef = useRef(null);
  const lastUpdateRef = useRef(0);
  const saveTimeoutRef = useRef(null);

  // 防抖保存用户偏好设置
  const saveUserPreferenceDebounced = useCallback((width) => {
    // 清除之前的延时保存
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }
    
    // 延时保存，避免拖拽过程中频繁写入localStorage
    saveTimeoutRef.current = setTimeout(() => {
      saveUserPreference(preferenceKey, width);
      console.log(`已保存面板宽度偏好设置: ${width}px`);
    }, 500); // 500ms后保存
  }, [preferenceKey]);

  // 内存优化：防抖设置宽度
  const setRightPanelWidthOptimized = useCallback((width) => {
    if (Math.abs(width - rightPanelWidth) > 1) { // 只有变化超过1px才更新
      setRightPanelWidth(width);
      // 同时保存用户偏好
      saveUserPreferenceDebounced(width);
    }
  }, [rightPanelWidth, saveUserPreferenceDebounced]);

  const handleMouseDown = useCallback((e) => {
    e.preventDefault();
    setIsDragging(true);
    setIsOptimized(true);
    
    // 更激进的性能优化
    if (containerRef.current) {
      containerRef.current.style.pointerEvents = 'none';
      const leftPanel = containerRef.current.children[0];
      const rightPanel = containerRef.current.children[2];
      
      if (leftPanel) {
        leftPanel.style.userSelect = 'none';
        leftPanel.style.pointerEvents = 'none';
        leftPanel.style.transform = 'translateZ(0)';
        leftPanel.style.willChange = 'width';
        // 暂时降低渲染质量
        leftPanel.style.backfaceVisibility = 'hidden';
        leftPanel.style.perspective = '1000px';
        // 减少重排和重绘
        leftPanel.style.contain = 'layout style paint';
      }
      
      if (rightPanel) {
        rightPanel.style.userSelect = 'none';
        rightPanel.style.pointerEvents = 'none';
        rightPanel.style.transform = 'translateZ(0)';
        rightPanel.style.willChange = 'width';
        rightPanel.style.contain = 'layout style paint';
      }
    }
    
    const throttleDelay = 8; // 提高到约120fps
    
    const handleMouseMove = (moveEvent) => {
      const now = performance.now(); // 使用更精确的时间
      if (now - lastUpdateRef.current < throttleDelay) return;
      lastUpdateRef.current = now;
      
      if (animationIdRef.current) {
        cancelAnimationFrame(animationIdRef.current);
      }
      
      animationIdRef.current = requestAnimationFrame(() => {
        if (!containerRef.current) return;
        
        const rect = containerRef.current.getBoundingClientRect();
        const containerWidth = rect.width;
        const newRightWidth = rect.right - moveEvent.clientX;
        
        // Apply constraints
        const clampedWidth = Math.min(
          Math.max(newRightWidth, rightMinWidth),
          containerWidth - leftMinWidth
        );
        
        // 使用优化的设置函数，会自动保存用户偏好
        setRightPanelWidthOptimized(clampedWidth);
      });
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      setIsOptimized(false);
      
      // 恢复原始样式
      if (containerRef.current) {
        containerRef.current.style.pointerEvents = '';
        const leftPanel = containerRef.current.children[0];
        const rightPanel = containerRef.current.children[2];
        
        if (leftPanel) {
          leftPanel.style.userSelect = '';
          leftPanel.style.pointerEvents = '';
          leftPanel.style.willChange = '';
          leftPanel.style.backfaceVisibility = '';
          leftPanel.style.perspective = '';
          leftPanel.style.contain = '';
        }
        
        if (rightPanel) {
          rightPanel.style.userSelect = '';
          rightPanel.style.pointerEvents = '';
          rightPanel.style.willChange = '';
          rightPanel.style.contain = '';
        }
      }
      
      if (animationIdRef.current) {
        cancelAnimationFrame(animationIdRef.current);
        animationIdRef.current = null;
      }
      
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };

    document.addEventListener('mousemove', handleMouseMove, { passive: true });
    document.addEventListener('mouseup', handleMouseUp);
  }, [leftMinWidth, rightMinWidth, setRightPanelWidthOptimized]);

  const handleDoubleClick = useCallback(() => {
    setRightPanelWidth(rightInitialWidth);
    // 保存重置后的偏好设置
    saveUserPreference(preferenceKey, rightInitialWidth);
    console.log(`已重置面板宽度并保存偏好设置: ${rightInitialWidth}px`);
  }, [rightInitialWidth, preferenceKey]);

  // 组件卸载时清理定时器
  useEffect(() => {
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, []);

  let containerStyle = {
    display: 'flex',
    height: '100vh',
    width: '100%',
    position: 'relative'
  };

  if (item.style) {
    containerStyle = { ...containerStyle, ...Tree.cssConverter(item.style) };
  }

  const children = Tree.renderChildren(item, item.annotation);
  const leftChild = children[0];
  const rightChild = children[1];

  const resizerStyle = {
    width: isDragging ? '4px' : (isHovering ? '2px' : '1px'),
    background: isDragging ? '#007bff' : 'transparent',
    cursor: 'ew-resize',
    userSelect: 'none',
    borderLeft: isDragging ? '1px solid #007bff' : (isHovering ? '1px solid rgba(0,0,0,0.1)' : 'none'),
    borderRight: 'none',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative',
    transition: isDragging ? 'none' : 'all 0.2s ease',
    zIndex: 1
  };

  const dotStyle = {
    color: isDragging ? '#007bff' : (isHovering ? 'rgba(0,0,0,0.4)' : 'transparent'),
    fontSize: '10px',
    transform: 'rotate(90deg)',
    opacity: isDragging ? 1 : (isHovering ? 0.6 : 0)
  };

  return (
    <div ref={containerRef} style={containerStyle}>
      {/* Left Panel */}
      <div style={{ 
        flex: 1,
        minWidth: `${leftMinWidth}px`,
        overflow: 'hidden',
        position: 'relative',
        // 动态性能优化
        willChange: isDragging ? 'width' : 'auto',
        transform: 'translateZ(0)',
        backfaceVisibility: 'hidden',
        // 拖拽时额外优化
        ...(isOptimized && {
          contain: 'layout style paint',
          isolation: 'isolate',
          // 降低渲染精度以提高性能
          imageRendering: 'optimizeSpeed',
          textRendering: 'optimizeSpeed'
        })
      }}>
        {leftChild}
      </div>
      
      {/* Resizer */}
      <div
        style={resizerStyle}
        onMouseDown={handleMouseDown}
        onDoubleClick={handleDoubleClick}
        onMouseEnter={() => setIsHovering(true)}
        onMouseLeave={() => setIsHovering(false)}
        title="拖拽调整面板大小，双击重置"
      >
        <span style={dotStyle}>︙</span>
      </div>
      
      {/* Right Panel */}
      <div style={{
        width: `${rightPanelWidth}px`,
        minWidth: `${rightMinWidth}px`,
        overflow: 'hidden',
        background: '#fafafa',
        borderLeft: '1px solid #ddd',
        position: 'relative',
        padding: '0 0px 0 0px' // padding
      }}>
        {rightChild}
      </div>
    </div>
  );
});

Registry.addTag("resizableview", ResizableViewModel, HtxResizableView);

export { HtxResizableView, ResizableViewModel }; 