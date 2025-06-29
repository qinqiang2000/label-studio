import React, { useCallback, useRef, useState } from "react";
import { observer } from "mobx-react";
import { types } from "mobx-state-tree";

import Registry from "../../core/Registry";
import Tree from "../../core/Tree";
import Types from "../../core/Types";
import VisibilityMixin from "../../mixins/Visibility";
import { AnnotationMixin } from "../../mixins/AnnotationMixin";

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
  
  const [rightPanelWidth, setRightPanelWidth] = useState(rightInitialWidth);
  const [isDragging, setIsDragging] = useState(false);
  const [isHovering, setIsHovering] = useState(false);
  const containerRef = useRef(null);

  const handleMouseDown = useCallback((e) => {
    e.preventDefault();
    setIsDragging(true);
    
    // 添加临时样式来提高拖拽性能
    if (containerRef.current) {
      containerRef.current.style.pointerEvents = 'none'; // 禁用子元素的鼠标事件
      const leftPanel = containerRef.current.children[0];
      const rightPanel = containerRef.current.children[2];
      if (leftPanel) {
        leftPanel.style.userSelect = 'none';
        leftPanel.style.pointerEvents = 'none';
        // 暂时降低PDF渲染质量
        leftPanel.style.transform = 'translateZ(0)'; // 启用硬件加速
      }
      if (rightPanel) {
        rightPanel.style.userSelect = 'none';
        rightPanel.style.pointerEvents = 'none';
      }
    }
    
    let animationId;
    let lastUpdate = 0;
    const throttleDelay = 16; // 约60fps
    
    const handleMouseMove = (moveEvent) => {
      const now = Date.now();
      if (now - lastUpdate < throttleDelay) return;
      lastUpdate = now;
      
      if (animationId) {
        cancelAnimationFrame(animationId);
      }
      
      animationId = requestAnimationFrame(() => {
        if (!containerRef.current) return;
        
        const rect = containerRef.current.getBoundingClientRect();
        const containerWidth = rect.width;
        const newRightWidth = rect.right - moveEvent.clientX;
        
        // Apply constraints
        const clampedWidth = Math.min(
          Math.max(newRightWidth, rightMinWidth),
          containerWidth - leftMinWidth
        );
        
        setRightPanelWidth(clampedWidth);
      });
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      
      // 恢复原始样式
      if (containerRef.current) {
        containerRef.current.style.pointerEvents = '';
        const leftPanel = containerRef.current.children[0];
        const rightPanel = containerRef.current.children[2];
        if (leftPanel) {
          leftPanel.style.userSelect = '';
          leftPanel.style.pointerEvents = '';
          leftPanel.style.transform = '';
        }
        if (rightPanel) {
          rightPanel.style.userSelect = '';
          rightPanel.style.pointerEvents = '';
        }
      }
      
      if (animationId) {
        cancelAnimationFrame(animationId);
      }
      
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  }, [leftMinWidth, rightMinWidth]);

  const handleDoubleClick = useCallback(() => {
    setRightPanelWidth(rightInitialWidth);
  }, [rightInitialWidth]);

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
        // 性能优化
        willChange: isDragging ? 'width' : 'auto',
        transform: 'translateZ(0)', // 启用硬件加速
        backfaceVisibility: 'hidden' // 避免不必要的重绘
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
        padding: '0 8px 0 8px' // 左侧12px，右侧8px的padding
      }}>
        {rightChild}
      </div>
    </div>
  );
});

Registry.addTag("resizableview", ResizableViewModel, HtxResizableView);

export { HtxResizableView, ResizableViewModel }; 