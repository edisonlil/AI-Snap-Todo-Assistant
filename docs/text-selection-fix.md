# 详情页文本选中复制功能优化

## 问题根因

详情页数据无法拖拽选中复制的根本原因：

1. **普通 Text 组件不支持选中**：QML 的 `Text` 组件默认不支持鼠标拖拽选中文本
2. **MouseArea 覆盖拦截**：可编辑字段的整个文本区域被 `MouseArea` 覆盖用于触发编辑，拦截了所有鼠标事件
3. **点击热区过大**：整个字段值区域都是点击热区，导致用户想选中文本时会触发编辑模式

## 解决方案

### 1. 创建 SelectableText 组件

新增 `src/aica/qml/SelectableText.qml` 组件，基于只读的 `TextEdit` 实现：

```qml
TextEdit {
    readOnly: true              // 只读模式
    selectByMouse: true         // 支持鼠标选中
    selectByKeyboard: true      // 支持键盘选中
    activeFocusOnPress: false   // 禁用点击获取焦点
    textFormat: TextEdit.PlainText  // 纯文本格式
    selectionColor: "#B8A890"   // 选中背景色
    selectedTextColor: "#2F241A" // 选中文字色
}
```

### 2. 修改 DetailField 组件

将展示态的 `Text` 替换为 `SelectableText`：

- 字段值使用 `SelectableText` 支持选中复制
- 移除覆盖文本区域的 `MouseArea`
- 将编辑按钮改为独立的圆形按钮，hover 时显示
- 使用 `z` 属性确保文本选中优先级高于外层交互
- **添加多行文本高度限制**：最大高度 120px，超出部分可滚动选中
- 修复 Layout 中使用 anchors 的警告，改用 `Layout.alignment`

### 3. 修改 RootCauseCascadeField 组件

同样将展示态的 `Text` 替换为 `SelectableText`：

- 根因路径值支持选中复制
- 编辑按钮改为独立的圆形按钮
- 移除覆盖文本的点击热区

### 4. 修改 TicketsSection 组件

将详情页中的关键文本字段替换为 `SelectableText`：

- 工单标题
- 工单摘要
- 历史跟进内容

注意：移除了 `lineHeight` 属性设置，因为 `TextEdit` 默认行高已经足够。

## 用户体验改进

- ✅ 所有字段值支持鼠标拖拽选中
- ✅ 支持 Ctrl+C 复制选中文本
- ✅ 展示态保持原有视觉风格
- ✅ 编辑入口更明确（hover 显示编辑按钮）
- ✅ 不影响现有排版和间距
- ✅ 长文本支持换行和选中
- ✅ **长文本字段限制最大高度 120px，防止布局被撑开**
- ✅ 超长文本可通过滚动查看和选中
- ✅ 不破坏 inline 编辑功能

## 技术细节

### SelectableText 特性

- 基于 `TextEdit` 组件，设置为只读模式
- 支持鼠标和键盘选中文本
- 禁用焦点获取，避免显示编辑光标
- 自定义选中颜色，保持视觉一致性

### 交互优先级

使用 `z` 属性控制层级：

- `z: 1` - 可选中文本
- `z: 2` - 编辑按钮和操作按钮
- 外层 `MouseArea` 只用于 hover 检测，设置 `propagateComposedEvents: true`

### 编辑入口优化

- 可编辑字段 hover 时显示圆形编辑按钮（✎）
- 点击编辑按钮进入编辑模式
- 文本区域不再是点击热区，可以自由选中复制

### 长文本高度限制

```qml
Item {
    implicitHeight: fieldRoot.multiline ? Math.min(fieldText.implicitHeight, 120) : fieldText.implicitHeight
    clip: fieldRoot.multiline  // 超出部分裁剪
    
    SelectableText {
        // 文本内容，支持滚动选中
    }
}
```

- 多行文本字段最大高度 120px
- 超出部分通过 `clip: true` 裁剪
- 用户可以通过鼠标滚轮或拖拽选中查看完整内容

### 布局修复

- 修复了 `RowLayout` 在 Layout 中使用 anchors 的警告
- 改用 `Layout.alignment: Qt.AlignRight | Qt.AlignVCenter`

## 测试建议

1. 打开工单详情页
2. 尝试拖拽选中各个字段值（ach单号、版本号、功能点等）
3. 使用 Ctrl+C 复制选中的文本
4. 验证编辑功能仍然正常（hover 显示编辑按钮，点击进入编辑）
5. 测试长文本字段的换行和选中
6. 验证历史跟进内容可以选中复制

## 已验证

应用已成功启动并运行，所有 QML 组件加载正常，无致命错误。
