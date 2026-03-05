# Feature Requests

This file tracks new feature requests and enhancements for the Workspace File Indexer.
When starting a new feature, pick the highest priority item from this list.
Update the status with `[x]` when completed.

## Future update 0001
- [x] 在右侧的路径列表中做修改,点击RelativePath,FileType,AbsolutePath这三个列头时,可以根据该列进行升序或降序排列,顺序为:升序->降序->升序... ✅ COMPLETED
- [x] 每种不同的FileType的路径,在右侧的路径列表中,这一行给一个不同的背景颜色,实现一个算法可以根据FileType生成不同的颜色,颜色要不要过于鲜艳,要和背景颜色与文本颜色有明显的区分度. ✅ COMPLETED
- [x] 添加快捷键F5,可以取消所有的排序,恢复成默认排序. ✅ COMPLETED
- [x] 自动测试. ✅ COMPLETED
- [x] Git Commit And Push. ✅ COMPLETED

## Future update 0002
- [x] Workspace编辑面板中目录可以设置隐藏规则,隐藏规则为正则表达式,英文分号分隔,请合理设计区域大小,隐藏规则的显示方式可以像Tag一样显示,点击Tag可以删除该隐藏规则,匹配隐藏规则的路径不会在主面板右侧的路径列表中显示. ✅ COMPLETED
- [x] 自动测试. ✅ COMPLETED
- [x] Git Commit And Push. ✅ COMPLETED

## Future update 0003 ✅ COMPLETED
- [x] 将SQLite的存储目录迁移到exe所在目录的.db目录中. ✅ COMPLETED
- [x] 迁移完成后删除公共目录的SQLite数据库文件. ✅ COMPLETED
- [x] 自动测试. ✅ COMPLETED
- [x] Git Commit And Push. ✅ COMPLETED 

## Future update 0004 ✅ COMPLETED
- [x] app启动后如果发现SQLite文件不存在,则创建并初始化SQLite,包括初始化文件,在数据库新建表. ✅ COMPLETED
- [x] 在Workspace编辑面板中,内容的行中HidingRules列下的按钮,点击后弹出一个可输入多行文本的弹窗,可以编辑该行的HidingRules,编辑完成后点击OK按钮保存,点击Cancel按钮取消. ✅ COMPLETED
- [x] 在Workspace编辑面板中,内容的行中HidingRules列下的按钮,调整按钮的大小,使其能够显示完整的文本,不要超出行高. ✅ COMPLETED
- [x] 自动测试. ✅ COMPLETED
- [x] Git Commit And Push. ✅ COMPLETED
 
 ## Future update 0005 ✅ COMPLETED
- [x] 在Workspace编辑面板中,内容的行中Remove按钮现在过宽了,保证文本显示的前提下缩小Remove按钮的宽度,使按钮不要超出当前单元格. ✅ COMPLETED
- [x] 在Workspace编辑面板中,内容的行中HidingRules列下的Edit按钮与调整后的Remove按钮大小一样. ✅ COMPLETED
- [x] 自动测试. ✅ COMPLETED
- [x] Git Commit And Push. ✅ COMPLETED

## Future update 0006 - CLI Command Enhancements for AI Agent Usage (MEDIUM PRIORITY) ✅ COMPLETED
- [x] Add `remove-tag` CLI command to remove tags from files (current CLI only supports adding tags) ✅ COMPLETED
- [x] Add `list-tags` CLI command to list all unique tags across all workspaces ✅ COMPLETED
- [x] Add `list-workspaces` CLI command to list all available workspaces ✅ COMPLETED
- [x] Add comprehensive tests for all new CLI commands (7 new tests added) ✅ COMPLETED
- [x] Update CLI help documentation and version (automatic via Click) ✅ COMPLETED
- [x] Git Commit And Push ✅ COMPLETED