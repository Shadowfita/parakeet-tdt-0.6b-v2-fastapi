# 测试数据准备指南

## 概述

ASR准确率评估工具已经创建完成。本指南将帮助你准备测试数据，包括如何获取或创建2小时的音频文件及其参考转录文本。

## 已创建的工具

### 1. 评估脚本
- **evaluate_asr.py** - 主评估脚本，支持长音频文件
- **example_evaluation.sh** - 快速评估脚本

### 2. 数据准备工具
- **prepare_test_data.py** - 从LibriSpeech下载数据（需要网络访问）
- **combine_audio_for_test.py** - 合并多个音频文件
- **create_demo_test.py** - 创建演示数据

### 3. 示例参考文本
在 `test_data/` 目录下已创建了三个示例参考文本：
- `reference_sample1.txt` (54词) - 经典pangram示例
- `reference_sample2.txt` (51词) - 语音识别技术描述
- `reference_sample3.txt` (62词) - 人工智能主题

## 获取测试数据的方法

### 方法1: 使用公开数据集（推荐）

#### LibriSpeech
最常用的英语ASR评估数据集。

**下载方式：**
```bash
# 下载test-clean子集 (约350MB)
wget http://www.openslr.org/resources/12/test-clean.tar.gz

# 或下载dev-clean子集 (约340MB)
wget http://www.openslr.org/resources/12/dev-clean.tar.gz

# 解压
tar -xzf test-clean.tar.gz
```

**数据结构：**
```
LibriSpeech/
├── test-clean/
│   ├── 1089/
│   │   ├── 134686/
│   │   │   ├── 1089-134686-0000.flac
│   │   │   ├── 1089-134686-0001.flac
│   │   │   └── 1089-134686.trans.txt
```

转录文件格式：
```
1089-134686-0000 HE BEGAN A CONFUSED COMPLAINT AGAINST THE WIZARD
1089-134686-0001 WHO HAD VANISHED BEHIND THE CURTAIN ON THE LEFT
```

#### Common Voice
Mozilla的多语言语音数据集，包含英语数据。

**下载地址：** https://commonvoice.mozilla.org/

**特点：**
- 包含完整的音频和转录
- 多种口音和说话人
- CSV格式的元数据

#### VoxPopuli
欧洲议会辩论录音，包含长时间音频。

**下载地址：** https://github.com/facebookresearch/voxpopuli

### 方法2: 从音视频内容创建测试数据

#### TED演讲
TED演讲有高质量的转录字幕。

**步骤：**
1. 选择一个TED演讲视频
2. 使用youtube-dl或类似工具下载音频：
   ```bash
   youtube-dl -x --audio-format wav <TED_TALK_URL>
   ```
3. 从TED网站下载对应的transcript
4. 清理和格式化transcript文本

#### 有声读物
可以使用Project Gutenberg的公版有声读物。

**资源：**
- LibriVox (https://librivox.org/) - 免费公版有声读物
- Project Gutenberg - 对应的文本

**步骤：**
1. 下载有声读物音频
2. 从Project Gutenberg获取对应的文本
3. 确保音频和文本完全对应

#### 播客
许多播客提供转录文本。

**建议的播客：**
- NPR programs (通常有transcript)
- 学术讲座和演讲
- 新闻广播节目

### 方法3: 录制你自己的测试数据

如果需要特定领域或口音的测试数据：

**步骤：**
1. 准备要录制的文本（可以使用test_data/中的示例文本）
2. 使用录音软件录制清晰的音频：
   ```bash
   # 使用arecord (Linux)
   arecord -f cd -t wav -d 300 output.wav

   # 或使用Audacity等图形界面工具
   ```
3. 确保音频质量：
   - 16kHz或更高采样率
   - 单声道
   - WAV格式
   - 最小背景噪音

### 方法4: 创建长时间测试音频（2小时）

要创建2小时的测试音频，你需要合并多个短音频文件。

#### 使用脚本合并
```bash
# 1. 准备多个音频文件（总时长约2小时）
# 2. 创建文件列表
cat > test_data/long_audio_list.txt << EOF
file '/path/to/audio1.wav'
file '/path/to/audio2.wav'
file '/path/to/audio3.wav'
# ... 更多文件
EOF

# 3. 使用ffmpeg合并
ffmpeg -f concat -safe 0 -i test_data/long_audio_list.txt \
  -ar 16000 -ac 1 test_data/audio_2hours.wav

# 4. 合并对应的转录文本
cat transcript1.txt transcript2.txt transcript3.txt > test_data/reference_2hours.txt
```

#### 计算需要的文件数量
假设每个音频片段平均5分钟，2小时需要约24个文件：
- 2小时 = 120分钟
- 120分钟 ÷ 5分钟/文件 = 24个文件

## 实际测试示例

### 示例1: 使用短音频测试（5分钟）

```bash
# 假设你有一个5分钟的音频和对应的转录
python evaluate_asr.py \
  --audio test_data/audio_5min.wav \
  --reference test_data/reference_5min.txt \
  --chunk-duration 30 \
  --output results_5min.json \
  --device cuda
```

### 示例2: 使用2小时音频测试

```bash
# 2小时音频会自动分块处理
python evaluate_asr.py \
  --audio test_data/audio_2hours.wav \
  --reference test_data/reference_2hours.txt \
  --chunk-duration 30 \
  --output results_2hours.json \
  --device cuda
```

**预期处理时间：**
- 使用GPU (RTX 3090): 约5-10分钟
- 使用CPU: 约1-2小时

### 示例3: 批量评估多个文件

```bash
# 创建批量评估脚本
cat > batch_evaluate.sh << 'EOF'
#!/bin/bash
for audio in test_data/audio_*.wav; do
    name=$(basename "$audio" .wav)
    ref="test_data/reference_${name#audio_}.txt"
    if [ -f "$ref" ]; then
        echo "Evaluating: $name"
        python evaluate_asr.py \
            --audio "$audio" \
            --reference "$ref" \
            --output "results_${name}.json"
    fi
done
EOF

chmod +x batch_evaluate.sh
./batch_evaluate.sh
```

## 预期评估结果

### 高质量音频（清晰，无噪音）
```
Word Error Rate (WER): 3-8%
Character Error Rate (CER): 1-4%
Word Accuracy: 92-97%
```

### 中等质量音频（轻微噪音，清晰说话）
```
Word Error Rate (WER): 8-15%
Character Error Rate (CER): 4-8%
Word Accuracy: 85-92%
```

### 困难音频（背景噪音，口音，专业术语）
```
Word Error Rate (WER): 15-30%
Character Error Rate (CER): 8-15%
Word Accuracy: 70-85%
```

## 快速开始建议

如果你现在就想测试评估工具，最简单的方法是：

### 选项A: 使用你自己的音频
如果你有任何音频文件（录音、播客、会议录音等）：
1. 人工转录一小段（5-10分钟即可）
2. 使用评估工具测试

### 选项B: 下载一个TED演讲
1. 选择一个短的TED演讲（10-15分钟）
2. 下载视频，提取音频
3. 从TED网站复制transcript
4. 运行评估

### 选项C: 录制测试音频
1. 使用 `test_data/reference_sample1.txt` 中的文本
2. 录制自己朗读这段文本
3. 保存为 `test_data/audio_sample1.wav`
4. 运行评估：
   ```bash
   python evaluate_asr.py \
     --audio test_data/audio_sample1.wav \
     --reference test_data/reference_sample1.txt \
     --output results_sample1.json
   ```

## 故障排除

### 问题: 找不到音频文件
**解决方案：** 确保音频文件路径正确，使用绝对路径

### 问题: 内存不足
**解决方案：**
- 减小 `--chunk-duration` 参数（如15秒）
- 使用CPU而不是GPU

### 问题: WER非常高（>50%）
**可能原因：**
- 参考文本与音频不匹配
- 音频质量很差
- 音频包含非语音内容（音乐、静音等）

### 问题: 处理速度很慢
**解决方案：**
- 确保使用GPU (`--device cuda`)
- 增大 `--chunk-duration` 参数
- 检查模型配置（使用fp16精度）

## 总结

评估工具已经准备就绪，现在你需要：

1. ✅ **评估脚本** - 已创建
2. ✅ **文档** - 已完成
3. ⏳ **音频数据** - 需要你提供或下载
4. ⏳ **参考文本** - 需要与音频对应

**建议的下一步：**
1. 选择上述方法之一获取测试数据
2. 准备音频和参考文本
3. 运行评估脚本
4. 分析结果

如果你有特定的音频文件或数据源，我可以帮助你准备相应的参考文本和运行评估。
