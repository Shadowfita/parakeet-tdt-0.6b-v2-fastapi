# LibriSpeech数据集使用指南

## 概述

本指南说明如何使用LibriSpeech数据集创建2小时（或其他时长）的音频测试文件，并进行ASR准确率评估。

## LibriSpeech数据集简介

LibriSpeech是一个公开的英语语音识别数据集，包含大约1000小时的朗读有声读物音频。

**特点：**
- 高质量录音（16kHz采样率）
- 准确的转录文本
- 多个说话人
- 公共领域授权

**子集：**
- `dev-clean` (5.4小时) - 验证集，清晰音频
- `test-clean` (5.4小时) - 测试集，清晰音频
- `dev-other` (5.3小时) - 验证集，困难音频
- `test-other` (5.4小时) - 测试集，困难音频
- `train-clean-100` (100小时) - 训练集
- `train-clean-360` (360小时) - 训练集
- `train-other-500` (500小时) - 训练集

## 完整工作流程

### 第1步：下载LibriSpeech数据集

#### 方法A：使用提供的脚本（推荐）

```bash
# 自动下载和解压
./download_librispeech.sh
```

该脚本会：
1. 尝试从多个镜像下载
2. 自动解压数据
3. 验证文件完整性

#### 方法B：手动下载

如果自动下载失败：

```bash
# 1. 手动下载（选择一个）
wget https://www.openslr.org/resources/12/dev-clean.tar.gz
# 或
curl -O https://www.openslr.org/resources/12/dev-clean.tar.gz

# 2. 解压到test_data目录
mkdir -p test_data
tar -xzf dev-clean.tar.gz -C test_data/

# 验证
ls test_data/LibriSpeech/dev-clean
```

#### 可选：下载其他子集

如果需要更多数据创建更长的音频：

```bash
# test-clean (5.4小时)
wget https://www.openslr.org/resources/12/test-clean.tar.gz
tar -xzf test-clean.tar.gz -C test_data/

# train-clean-100 (100小时) - 创建超长测试音频
wget https://www.openslr.org/resources/12/train-clean-100.tar.gz
tar -xzf train-clean-100.tar.gz -C test_data/
```

### 第2步：处理LibriSpeech数据

运行处理脚本，它会：
- 查找所有音频文件（.flac格式）
- 解析转录文本文件
- 创建不同时长的测试样本
- 生成音频文件列表和参考文本

```bash
python3 process_librispeech.py
```

**输出示例：**
```
LIBRISPEECH DATA PROCESSOR
==============================================================================

✓ LibriSpeech directory found: test_data/LibriSpeech/dev-clean

Searching for FLAC files...
  Found 2703 FLAC files

Parsing transcripts...
  Parsed 2703 transcripts

CREATING TEST SAMPLES
==============================================================================

Creating short sample (~5 minutes)...
  Selected 10 files, duration: 64.2s
  ✓ short sample created:
    Files: 62
    Duration: 301.5s (5.0 minutes)
    Words: 845

Creating medium sample (~15 minutes)...
  ✓ medium sample created:
    Files: 185
    Duration: 905.2s (15.1 minutes)
    Words: 2541

Creating long sample (~30 minutes)...
  ✓ long sample created:
    Files: 370
    Duration: 1798.4s (30.0 minutes)
    Words: 5043

Creating xlarge sample (~1 hour)...
  ✓ xlarge sample created:
    Files: 742
    Duration: 3605.7s (60.1 minutes)
    Words: 10124

Creating 2hours sample (~2 hours)...
  ✓ 2hours sample created:
    Files: 1485
    Duration: 7201.3s (120.0 minutes)
    Words: 20248

SAVING SAMPLE FILES
==============================================================================

  Saved: reference_short.txt and filelist_short.txt
  Saved: reference_medium.txt and filelist_medium.txt
  Saved: reference_long.txt and filelist_long.txt
  Saved: reference_xlarge.txt and filelist_xlarge.txt
  Saved: reference_2hours.txt and filelist_2hours.txt

✓ Metadata saved: test_data/librispeech_samples.json
```

**生成的文件：**
- `test_data/reference_*.txt` - 参考转录文本
- `test_data/filelist_*.txt` - 音频文件列表
- `test_data/librispeech_samples.json` - 元数据

### 第3步：合并音频文件

运行音频合并脚本：

```bash
python3 combine_librispeech_audio.py
```

**交互式菜单：**
```
LIBRISPEECH AUDIO COMBINER
==============================================================================

Available samples:
  1. short      - ~5 minutes      (5.0 min, 62 files)
  2. medium     - ~15 minutes     (15.1 min, 185 files)
  3. long       - ~30 minutes     (30.0 min, 370 files)
  4. xlarge     - ~1 hour         (60.1 min, 742 files)
  5. 2hours     - ~2 hours        (120.0 min, 1485 files)
  6. All samples

Select sample to create (1-6, or 'q' to quit): 5
```

**选择"5"会创建2小时音频：**
```
Creating 2hours audio (120.0 min, 1485 files)
  Input list: test_data/filelist_2hours.txt
  Output: test_data/audio_2hours.wav
  Running ffmpeg...
  ✓ Audio file created successfully
  Size: 230.4 MB
  Duration: 7201.3s (2.00 hours)
```

#### 手动合并（如果需要）

也可以直接使用ffmpeg命令：

```bash
# 创建2小时音频
ffmpeg -f concat -safe 0 -i test_data/filelist_2hours.txt \
  -ar 16000 -ac 1 test_data/audio_2hours.wav

# 创建其他时长
ffmpeg -f concat -safe 0 -i test_data/filelist_short.txt \
  -ar 16000 -ac 1 test_data/audio_short.wav
```

### 第4步：运行ASR评估

现在可以评估ASR准确率了！

#### 评估2小时音频

```bash
python evaluate_asr.py \
  --audio test_data/audio_2hours.wav \
  --reference test_data/reference_2hours.txt \
  --chunk-duration 30 \
  --output results_2hours.json \
  --device cuda
```

**预期输出：**
```
================================================================================
ASR EVALUATION RESULTS
================================================================================

📁 Audio File: test_data/audio_2hours.wav
⏱️  Audio Duration: 7201.30s (120.02 minutes)
⚡ Transcription Time: 360.50s
🚀 Real-Time Factor (RTF): 0.0501x

--------------------------------------------------------------------------------
ACCURACY METRICS
--------------------------------------------------------------------------------
📊 Word Error Rate (WER): 5.23%
📊 Character Error Rate (CER): 2.15%
✅ Word Accuracy: 94.77%
✅ Character Accuracy: 97.85%

--------------------------------------------------------------------------------
TEXT COMPARISON
--------------------------------------------------------------------------------

📝 Reference (20248 words):
   MISTER QUILTER IS THE APOSTLE OF THE MIDDLE CLASSES AND WE ARE GLAD...

🎤 Hypothesis (20282 words):
   MISTER QUILTER IS THE APOSTLE OF THE MIDDLE CLASSES AND WE ARE GLAD...

================================================================================
```

#### 评估其他时长的音频

```bash
# 短音频测试 (5分钟)
python evaluate_asr.py \
  --audio test_data/audio_short.wav \
  --reference test_data/reference_short.txt \
  --output results_short.json

# 中等音频测试 (15分钟)
python evaluate_asr.py \
  --audio test_data/audio_medium.wav \
  --reference test_data/reference_medium.txt \
  --output results_medium.json

# 长音频测试 (30分钟)
python evaluate_asr.py \
  --audio test_data/audio_long.wav \
  --reference test_data/reference_long.txt \
  --output results_long.json

# 超长音频测试 (1小时)
python evaluate_asr.py \
  --audio test_data/audio_xlarge.wav \
  --reference test_data/reference_xlarge.txt \
  --output results_xlarge.json
```

### 第5步：批量评估

创建批量评估脚本：

```bash
cat > batch_evaluate_librispeech.sh << 'EOF'
#!/bin/bash

for sample in short medium long xlarge 2hours; do
    echo ""
    echo "===================================================================="
    echo "Evaluating: $sample"
    echo "===================================================================="

    python evaluate_asr.py \
        --audio test_data/audio_${sample}.wav \
        --reference test_data/reference_${sample}.txt \
        --chunk-duration 30 \
        --output results_${sample}.json \
        --device cuda

    echo ""
    echo "Results saved to: results_${sample}.json"
    echo ""
done

echo ""
echo "===================================================================="
echo "All evaluations complete!"
echo "===================================================================="
echo ""
echo "Summary of results:"
for sample in short medium long xlarge 2hours; do
    if [ -f "results_${sample}.json" ]; then
        wer=$(jq -r '.metrics.wer' results_${sample}.json)
        cer=$(jq -r '.metrics.cer' results_${sample}.json)
        duration=$(jq -r '.audio_duration' results_${sample}.json)
        minutes=$(echo "scale=1; $duration / 60" | bc)
        echo "  $sample (${minutes}min): WER=${wer}%, CER=${cer}%"
    fi
done
EOF

chmod +x batch_evaluate_librispeech.sh
./batch_evaluate_librispeech.sh
```

## 目录结构

完成所有步骤后，你的目录结构应该是：

```
parakeet-tdt-0.6b-v2-fastapi/
├── test_data/
│   ├── LibriSpeech/
│   │   └── dev-clean/          # 原始LibriSpeech数据
│   │       ├── 1272/
│   │       ├── 1988/
│   │       └── ...
│   ├── reference_short.txt     # 参考文本
│   ├── reference_medium.txt
│   ├── reference_long.txt
│   ├── reference_xlarge.txt
│   ├── reference_2hours.txt
│   ├── filelist_short.txt      # 音频文件列表
│   ├── filelist_medium.txt
│   ├── filelist_long.txt
│   ├── filelist_xlarge.txt
│   ├── filelist_2hours.txt
│   ├── audio_short.wav         # 合并的音频文件
│   ├── audio_medium.wav
│   ├── audio_long.wav
│   ├── audio_xlarge.wav
│   ├── audio_2hours.wav
│   └── librispeech_samples.json
├── results_short.json          # 评估结果
├── results_medium.json
├── results_long.json
├── results_xlarge.json
└── results_2hours.json
```

## 磁盘空间需求

| 项目 | 大小 | 说明 |
|------|------|------|
| dev-clean.tar.gz | ~337 MB | 压缩包 |
| dev-clean（解压） | ~1.0 GB | FLAC音频文件 |
| audio_short.wav | ~6 MB | 5分钟WAV |
| audio_medium.wav | ~17 MB | 15分钟WAV |
| audio_long.wav | ~35 MB | 30分钟WAV |
| audio_xlarge.wav | ~69 MB | 1小时WAV |
| audio_2hours.wav | ~138 MB | 2小时WAV |
| **总计** | **~1.6 GB** | 所有文件 |

## 处理时间估算

### GPU处理（NVIDIA GPU with CUDA）

| 音频时长 | 处理时间 | RTF |
|----------|---------|-----|
| 5分钟 | ~15秒 | 0.05x |
| 15分钟 | ~45秒 | 0.05x |
| 30分钟 | ~1.5分钟 | 0.05x |
| 1小时 | ~3分钟 | 0.05x |
| 2小时 | ~6分钟 | 0.05x |

### CPU处理

| 音频时长 | 处理时间 | RTF |
|----------|---------|-----|
| 5分钟 | ~5分钟 | 1.0x |
| 15分钟 | ~15分钟 | 1.0x |
| 30分钟 | ~30分钟 | 1.0x |
| 1小时 | ~1小时 | 1.0x |
| 2小时 | ~2-3小时 | 1.0-1.5x |

## 预期评估结果

LibriSpeech dev-clean是高质量音频，预期WER：

| 模型类型 | 预期WER | 说明 |
|----------|---------|------|
| 优秀模型 | 3-5% | 商业级ASR系统 |
| 良好模型 | 5-10% | 高质量开源模型 |
| 可用模型 | 10-15% | 一般开源模型 |

Parakeet-TDT 0.6B v2预期在LibriSpeech上达到5-8% WER。

## 故障排除

### 问题1：下载失败

**现象：** `wget: ERROR 403: Forbidden` 或连接超时

**解决方案：**
1. 尝试使用VPN或代理
2. 从备用镜像下载
3. 手动从浏览器下载
4. 使用其他数据集（Common Voice等）

### 问题2：解压失败

**现象：** `gzip: stdin: not in gzip format`

**解决方案：**
1. 检查下载的文件是否完整：`ls -lh dev-clean.tar.gz`
2. 验证文件类型：`file dev-clean.tar.gz`
3. 重新下载文件
4. 检查网络代理设置

### 问题3：ffmpeg不可用

**现象：** `ffmpeg: command not found`

**解决方案：**
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# 或下载静态构建版本
wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
```

### 问题4：音频合并时内存不足

**解决方案：**
1. 分批处理：先创建小的测试样本
2. 使用较小的子集（如只用一半的文件）
3. 增加系统swap空间

### 问题5：评估时GPU内存不足

**解决方案：**
1. 减小chunk-duration参数：`--chunk-duration 15`
2. 使用CPU：`--device cpu`
3. 减小batch size（在config中设置）

## 高级用法

### 创建自定义时长的音频

修改 `process_librispeech.py` 中的 `target_durations`：

```python
target_durations = [
    ("custom", 10800, "~3 hours"),  # 3小时
    ("huge", 18000, "~5 hours"),     # 5小时
]
```

### 混合不同数据集

```bash
# 下载多个子集
wget https://www.openslr.org/resources/12/dev-clean.tar.gz
wget https://www.openslr.org/resources/12/test-clean.tar.gz

# 解压到同一目录
tar -xzf dev-clean.tar.gz -C test_data/
tar -xzf test-clean.tar.gz -C test_data/

# 处理脚本会自动找到所有音频
python3 process_librispeech.py
```

### 选择特定说话人

修改 `process_librispeech.py` 添加说话人过滤：

```python
# 只选择特定说话人的音频
speaker_ids = ['1272', '1988', '2300']
audio_files = [f for f in audio_files
               if any(f.parent.parent.name == sid for sid in speaker_ids)]
```

## 总结

使用LibriSpeech数据集的完整流程：

1. ✅ **下载数据**: `./download_librispeech.sh`
2. ✅ **处理数据**: `python3 process_librispeech.py`
3. ✅ **合并音频**: `python3 combine_librispeech_audio.py`
4. ✅ **运行评估**: `python3 evaluate_asr.py --audio ... --reference ...`
5. ✅ **分析结果**: 查看JSON输出文件

**关键优势：**
- 高质量标准化数据集
- 准确的转录文本
- 可重复的评估结果
- 与研究社区基准对比

**下一步：**
- 尝试不同时长的测试
- 比较GPU vs CPU性能
- 测试不同的chunk-duration设置
- 与其他ASR系统对比
