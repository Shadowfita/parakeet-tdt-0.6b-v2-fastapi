# ASR准确率评估指南

本指南说明如何使用 `evaluate_asr.py` 脚本评估Parakeet-TDT ASR模型的准确率。

## 概述

`evaluate_asr.py` 脚本可以：
- 处理任意长度的音频文件（包括2小时以上的长音频）
- 自动分块处理长音频以避免内存问题
- 计算 WER (词错误率) 和 CER (字符错误率)
- 生成详细的评估报告
- 计算实时因子 (RTF)

## 前置准备

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

新增的依赖包括：
- `jiwer`: 用于计算WER和CER指标
- `tqdm`: 用于显示进度条

### 2. 准备评估数据

你需要准备两个文件：

#### a) 音频文件
- 支持格式: WAV, MP3, FLAC, M4A等
- 可以是任意长度（脚本会自动分块处理）
- 示例: `audio_2hours.wav`

#### b) 参考文本文件
- 纯文本文件，包含音频的准确转录
- UTF-8编码
- 示例: `reference_text.txt`

**参考文本示例** (`reference_text.txt`):
```text
This is the accurate transcription of the audio file.
It should contain the exact words spoken in the audio.
Make sure the text is properly formatted and accurate.
```

## 使用方法

### 基础用法

```bash
python evaluate_asr.py \
  --audio /path/to/audio_file.wav \
  --reference /path/to/reference_text.txt
```

### 处理2小时音频文件

```bash
python evaluate_asr.py \
  --audio /path/to/2hour_audio.wav \
  --reference /path/to/reference_text.txt \
  --chunk-duration 30 \
  --output evaluation_results.json
```

### 完整参数说明

| 参数 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `--audio` | 是 | - | 音频文件路径 |
| `--reference` | 是 | - | 参考文本文件路径 |
| `--output` | 否 | evaluation_results.json | 输出结果JSON文件路径 |
| `--chunk-duration` | 否 | 30.0 | 音频分块长度（秒） |
| `--device` | 否 | cuda/cpu | 推理设备 |

### 使用CPU进行评估

```bash
python evaluate_asr.py \
  --audio audio.wav \
  --reference reference.txt \
  --device cpu
```

## 评估指标说明

### WER (Word Error Rate) - 词错误率

WER衡量转录文本与参考文本在词级别上的差异：

```
WER = (S + D + I) / N × 100%
```

其中：
- S (Substitutions): 替换的词数
- D (Deletions): 删除的词数
- I (Insertions): 插入的词数
- N: 参考文本的总词数

**解读**:
- WER = 0%: 完美匹配
- WER < 5%: 优秀
- WER < 10%: 良好
- WER < 20%: 可接受
- WER > 20%: 需要改进

### CER (Character Error Rate) - 字符错误率

CER衡量转录文本与参考文本在字符级别上的差异：

```
CER = (S + D + I) / N × 100%
```

其中：
- S (Substitutions): 替换的字符数
- D (Deletions): 删除的字符数
- I (Insertions): 插入的字符数
- N: 参考文本的总字符数

**解读**:
- CER通常比WER低
- CER对拼写错误更敏感

### RTF (Real-Time Factor) - 实时因子

RTF表示转录速度与音频实时播放速度的比值：

```
RTF = 处理时间 / 音频时长
```

**解读**:
- RTF < 1.0: 比实时更快（例如RTF=0.5表示处理速度是实时的2倍）
- RTF = 1.0: 实时处理
- RTF > 1.0: 慢于实时

## 输出结果

### 控制台输出示例

```
================================================================================
ASR EVALUATION RESULTS
================================================================================

📁 Audio File: /path/to/audio.wav
⏱️  Audio Duration: 7200.00s (120.00 minutes)
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

📝 Reference (1234 words):
   This is the accurate transcription of the audio file...

🎤 Hypothesis (1240 words):
   This is the accurate transcription of the audio file...

================================================================================
```

### JSON输出文件

结果会保存到JSON文件（默认 `evaluation_results.json`）：

```json
{
  "audio_path": "/path/to/audio.wav",
  "audio_duration": 7200.0,
  "transcription_time": 360.5,
  "rtf": 0.0501,
  "hypothesis": "转录结果...",
  "reference": "参考文本...",
  "metrics": {
    "wer": 5.23,
    "cer": 2.15,
    "word_accuracy": 94.77,
    "char_accuracy": 97.85,
    "reference_words": 1234,
    "hypothesis_words": 1240
  }
}
```

## 准备测试数据

### 方法1: 使用现有音频和人工标注

1. 准备一个2小时的音频文件
2. 人工转录或使用高质量的现有转录
3. 将转录保存为文本文件

### 方法2: 使用公开数据集

推荐的数据集：
- **LibriSpeech**: 英语有声读物
  - 下载地址: https://www.openslr.org/12
  - 包含音频和对应的转录文本

- **Common Voice**: 多语言众包语音数据
  - 下载地址: https://commonvoice.mozilla.org/

### 方法3: 创建合成测试数据

```bash
# 示例：从多个短音频合并成长音频
ffmpeg -f concat -safe 0 -i filelist.txt -c copy output_2hours.wav
```

`filelist.txt` 内容：
```
file 'audio1.wav'
file 'audio2.wav'
file 'audio3.wav'
...
```

## 批量评估多个文件

创建一个批量评估脚本 `batch_evaluate.sh`:

```bash
#!/bin/bash

AUDIO_DIR="./test_audios"
REFERENCE_DIR="./references"
OUTPUT_DIR="./evaluation_results"

mkdir -p $OUTPUT_DIR

for audio_file in $AUDIO_DIR/*.wav; do
    filename=$(basename "$audio_file" .wav)
    reference_file="$REFERENCE_DIR/${filename}.txt"
    output_file="$OUTPUT_DIR/${filename}_results.json"

    if [ -f "$reference_file" ]; then
        echo "Evaluating: $filename"
        python evaluate_asr.py \
            --audio "$audio_file" \
            --reference "$reference_file" \
            --output "$output_file"
    else
        echo "Warning: Reference not found for $filename"
    fi
done
```

使用方法：

```bash
chmod +x batch_evaluate.sh
./batch_evaluate.sh
```

## 性能优化建议

### 处理长音频文件

1. **调整分块大小**:
   - 较长的分块（如60秒）可以减少处理次数，但需要更多内存
   - 较短的分块（如15秒）占用内存少，但处理次数多
   - 推荐使用30秒作为平衡点

2. **使用GPU加速**:
   ```bash
   python evaluate_asr.py \
     --audio audio.wav \
     --reference reference.txt \
     --device cuda
   ```

3. **批处理**:
   - 如果有多个2小时音频文件，可以串行处理以避免内存问题

## 常见问题

### Q1: 如果没有参考文本怎么办？

A: ASR准确率评估必须要有参考文本（ground truth）。你可以：
- 人工转录音频
- 使用高质量的现有转录
- 使用其他ASR系统的输出作为参考（但不够准确）

### Q2: WER很高怎么办？

A: 可能的原因：
1. 音频质量差（噪音、回声等）
2. 说话人口音重
3. 参考文本不准确
4. 模型不适合该音频领域

### Q3: 内存不足怎么办？

A:
1. 减小 `--chunk-duration` 参数
2. 使用CPU而不是GPU（`--device cpu`）
3. 关闭其他占用GPU内存的程序

### Q4: 处理速度太慢怎么办？

A:
1. 使用GPU（`--device cuda`）
2. 增大 `--chunk-duration` 参数
3. 确保使用了模型优化（fp16精度等）

## 示例工作流程

### 评估2小时音频文件的完整流程

```bash
# 1. 确保依赖已安装
pip install -r requirements.txt

# 2. 准备数据
# - 音频文件: audio_2hours.wav
# - 参考文本: reference_2hours.txt

# 3. 运行评估
python evaluate_asr.py \
  --audio audio_2hours.wav \
  --reference reference_2hours.txt \
  --chunk-duration 30 \
  --output results_2hours.json \
  --device cuda

# 4. 查看结果
cat results_2hours.json | jq '.metrics'
```

## 进阶使用

### 自定义文本规范化

编辑 `evaluate_asr.py` 中的 `normalize_text` 方法来自定义文本处理：

```python
def normalize_text(self, text: str) -> str:
    # 转小写
    text = text.lower()

    # 移除标点符号（可选）
    text = re.sub(r'[^\w\s]', '', text)

    # 规范化数字
    # text = self.normalize_numbers(text)

    # 移除多余空格
    text = ' '.join(text.split())

    return text.strip()
```

### 添加详细的错误分析

可以使用 `jiwer` 库的更多功能来分析具体的错误类型：

```python
from jiwer import wer, cer, compute_measures

measures = compute_measures(reference, hypothesis)
print(f"Substitutions: {measures['substitutions']}")
print(f"Deletions: {measures['deletions']}")
print(f"Insertions: {measures['insertions']}")
```

## 总结

使用本评估工具，你可以：
1. 快速评估ASR模型在长音频上的性能
2. 获取详细的准确率指标（WER、CER）
3. 分析转录质量和处理速度
4. 导出结果用于进一步分析

如有问题，请参考代码注释或提交Issue。
