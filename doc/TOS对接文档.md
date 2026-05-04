# TOS 对象存储对接文档

## 概述

本项目使用火山引擎 TOS (Tinder Object Storage) 作为对象存储服务，用于存储和分发视频文件。

---

## 1. 后端 TOS 对接代码 (server.py)

### 1.1 配置项

```python
# TOS配置
TOS_AK = "YOUR_TOS_ACCESS_KEY"
TOS_SK = "YOUR_TOS_SECRET_KEY"
TOS_ENDPOINT = "tos-cn-beijing.volces.com"
TOS_BUCKET_NAME = "fivesd"
TOS_REGION = "cn-beijing"

# 全局TOS客户端（懒加载）
tos_client = None
```

### 1.2 上传接口实现

```python
@app.route('/api/upload-tos-video', methods=['POST'])
def upload_tos_video():
    log_separator()
    log_info("收到TOS视频上传请求！")
    log_separator()
    
    try:
        log_request()
        log_info("接口: /api/upload-tos-video")
        log_info("方法: POST")
        
        if 'video' not in request.files:
            log_error("没有上传视频")
            return jsonify({"success": False, "error": "没有上传视频"}), 400
        
        file = request.files['video']
        log_info(f"上传的文件:")
        log_info(f"  Filename: {file.filename}")
        log_info(f"  Content-Type: {file.content_type}")
        
        # 生成唯一文件名
        file_ext = os.path.splitext(file.filename)[1]
        if not file_ext:
            file_ext = ".mp4"
        unique_filename = f"video_{uuid.uuid4().hex}{file_ext}"
        
        # 保存到临时文件
        temp_dir = tempfile.gettempdir()
        temp_file_path = os.path.join(temp_dir, unique_filename)
        file.save(temp_file_path)
        log_info(f"  临时保存路径: {temp_file_path}")
        log_info(f"  TOS文件名: {unique_filename}")
        
        log_info("正在上传到TOS...")
        
        # 导入tos模块并初始化客户端（放在函数开头，避免作用域问题）
        import tos
        global tos_client
        
        if tos_client is None:
            log_info("初始化TOS客户端...")
            tos_client = tos.TosClientV2(TOS_AK, TOS_SK, TOS_ENDPOINT, TOS_REGION)
        
        # 上传到TOS
        result = tos_client.put_object_from_file(
            bucket=TOS_BUCKET_NAME,
            key=unique_filename,
            file_path=temp_file_path,
            acl=tos.ACLType.ACL_Public_Read
        )
        
        # 拼接公网URL
        public_url = f"https://{TOS_BUCKET_NAME}.{TOS_ENDPOINT}/{unique_filename}"
        
        log_success("TOS上传成功！")
        log_info(f"公网链接: {public_url}")
        
        # 清理临时文件
        try:
            os.remove(temp_file_path)
        except:
            pass
        
        return jsonify({
            "success": True,
            "public_url": public_url,
            "filename": unique_filename
        })
        
    except Exception as e:
        log_error(f"TOS上传出错: {str(e)}")
        import traceback
        log_error(f"堆栈信息:\n{traceback.format_exc()}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
    finally:
        log_separator()
```

---

## 2. 前端 TOS 上传代码 (index.html)

### 2.1 核心上传函数

```javascript
async function uploadVideoToTOS(file, index) {
    const formData = new FormData();
    formData.append('video', file);
    
    try {
        const response = await fetch('/api/upload-tos-video', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            videoRefActualUrls[index] = result.public_url;
            videoRefUploading[index] = false;
            // 更新显示
            updateVideoRefGrid();
            return result.public_url;
        } else {
            alert('上传失败：' + result.error);
            removeMultiFile(index);
            return null;
        }
    } catch (e) {
        alert('上传失败：' + e.message);
        removeMultiFile(index);
        return null;
    }
}
```

### 2.2 文件上传处理逻辑

```javascript
function setupVideoRefUpload() {
    const addBtn = document.getElementById('video-ref-add-item');
    const input = document.getElementById('video-ref-file');
    
    addBtn.addEventListener('click', () => input.click());
    input.addEventListener('change', () => {
        Array.from(input.files).forEach(file => {
            if (videoRefFiles.length < videoRefMaxCount) {
                const index = videoRefFiles.length;
                videoRefFiles.push(file);
                videoRefUploading.push(file.type.startsWith('video'));
                videoRefActualUrls.push(null);
                
                if (file.type.startsWith('video')) {
                    // 视频文件：先显示预览，然后上传TOS
                    const reader = new FileReader();
                    reader.onload = (e) => {
                        videoRefUrls.push(e.target.result);
                        videoRefTypes.push(file.type);
                        updateVideoRefGrid();
                        // 开始上传到TOS
                        uploadVideoToTOS(file, index);
                    };
                    reader.readAsDataURL(file);
                } else {
                    // 图片和音频：直接用base64
                    const reader = new FileReader();
                    reader.onload = (e) => {
                        videoRefUrls.push(e.target.result);
                        videoRefActualUrls.push(e.target.result);
                        videoRefTypes.push(file.type);
                        updateVideoRefGrid();
                    };
                    reader.readAsDataURL(file);
                }
            }
        });
    });
}
```

### 2.3 上传状态检查

```javascript
// 检查是否有视频还在上传中
if (currentVideoMode === 'reference') {
    const uploadingVideos = videoRefUploading.filter(u => u);
    if (uploadingVideos.length > 0) {
        alert('还有' + uploadingVideos.length + '个视频正在上传到TOS，请稍候...');
        return;
    }
}
```

### 2.4 上传状态显示

```javascript
if (isUploading) {
    // 上传中的状态
    const loading = document.createElement('div');
    loading.className = 'upload-item-loading';
    loading.style.cssText = 'display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;color:#667eea;';
    
    const spinner = document.createElement('div');
    spinner.style.cssText = 'width:32px;height:32px;border:3px solid #e5e7eb;border-top-color:#667eea;border-radius:50%;animation:spin 0.8s linear infinite;margin-bottom:10px;';
    
    const text = document.createElement('div');
    text.style.fontSize = '12px';
    text.textContent = '上传到TOS...';
    
    loading.appendChild(spinner);
    loading.appendChild(text);
    item.appendChild(loading);
}
```

---

## 3. 使用流程

### 3.1 前端流程

1. 用户在视频制作界面选择"全能参考"模式
2. 用户上传视频文件
3. 前端检测到视频文件后，立即调用 `uploadVideoToTOS()` 函数
4. 同时显示"上传到TOS..."状态
5. 上传完成后，获取公网URL并更新显示
6. 用户点击生成时，检查是否还有上传中的视频

### 3.2 后端流程

1. 接收前端上传的文件
2. 生成唯一文件名
3. 保存到临时文件
4. 初始化TOS客户端（如果尚未初始化）
5. 上传文件到TOS
6. 设置文件访问权限为公开读
7. 返回公网URL
8. 清理临时文件

---

## 4. 配置说明

### 4.1 环境要求

- Python 3.x
- Flask
- TOS Python SDK

### 4.2 配置参数

| 参数 | 说明 | 示例值 |
|------|------|--------|
| TOS_AK | 访问密钥ID | your_access_key |
| TOS_SK | 访问密钥Secret | your_secret_key |
| TOS_ENDPOINT | TOS服务端点 | tos-cn-beijing.volces.com |
| TOS_BUCKET_NAME | 存储桶名称 | fivesd |
| TOS_REGION | 区域代码 | cn-beijing |

### 4.3 权限设置

- 文件上传后设置为 `ACL_Public_Read`，允许公网访问
- 公网URL格式：`https://{bucket}.{endpoint}/{filename}`

---

## 5. 注意事项

1. **安全性**：TOS密钥已硬编码在代码中，生产环境应使用环境变量
2. **文件类型**：目前主要处理 `.mp4` 视频文件
3. **临时文件**：上传成功后会自动清理临时文件
4. **并发上传**：支持同时上传多个视频文件
5. **错误处理**：上传失败时会删除该文件并提示用户

---

## 6. API 接口文档

### POST /api/upload-tos-video

上传视频到TOS对象存储

**请求参数：**
- FormData: `video` - 视频文件

**响应示例：**

成功：
```json
{
    "success": true,
    "public_url": "https://fivesd.tos-cn-beijing.volces.com/video_abc123def456.mp4",
    "filename": "video_abc123def456.mp4"
}
```

失败：
```json
{
    "success": false,
    "error": "错误描述"
}
```
