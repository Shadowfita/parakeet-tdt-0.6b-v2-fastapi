# LibriSpeech工具集 - README

## 快速开始

如果你想快速使用LibriSpeech数据集创建2小时音频并评估ASR准确率：

```bash
# 一键式快速开始
./quick_start_librispeech.sh
```

按照交互式提示选择测试样本，脚本会自动：
1. 下载LibriSpeech数据集
2. 处理音频和转录文本
3. 合并音频文件
4. 运行ASR评估
5. 显示结果

## 工具文件说明

### 核心工具

| 文件 | 用途 | 说明 |
|------|------|------|
| `quick_start_librispeech.sh` | 一键式快速开始 | 自动化整个流程 |
| `download_librispeech.sh` | 下载数据集 | 从多个镜像下载，自动解压 |
| `process_librispeech.py` | 处理数据 | 解析转录，创建测试样本 |
| `combine_librispeech_audio.py` | 合并音频 | 使用ffmpeg合并音频文件 |
| `LIBRISPEECH_GUIDE.md` | 完整指南 | 详细的使用说明和文档 |

### 手动使用流程

如果你想手动控制每一步：

```bash
# 步骤1: 下载LibriSpeech (337MB)
./download_librispeech.sh

# 步骤2: 处理数据
python3 process_librispeech.py

# 步骤3: 合并音频
python3 combine_librispeech_audio.py
# 选择要创建的样本

# 步骤4: 运行评估
python3 evaluate_asr.py \
  --audio test_data/audio_2hours.wav \
  --reference test_data/reference_2hours.txt \
  --output results_2hours.json \
  --device cuda
```

## 可用的测试样本

处理LibriSpeech后，可以创建以下测试样本：

| 样本名称 | 时长 | 文件数 | 词数 | 适用场景 |
|---------|------|--------|------|---------|
| short | ~5分钟 | ~62 | ~845 | 快速测试 |
| medium | ~15分钟 | ~185 | ~2,541 | 中等测试 |
| long | ~30分钟 | ~370 | ~5,043 | 全面测试 |
| xlarge | ~1小时 | ~742 | ~10,124 | 扩展测试 |
| 2hours | ~2小时 | ~1,485 | ~20,248 | 完整测试 |

## 输出文件

运行工具后会生成以下文件：

```
test_data/
├── LibriSpeech/dev-clean/       # 原始数据
├── reference_*.txt              # 参考转录文本
├── filelist_*.txt               # 音频文件列表
├── audio_*.wav                  # 合并的测试音频
└── librispeech_samples.json     # 元数据

results_*.json                   # 评估结果
```

## 预期结果

使用Parakeet-TDT 0.6B v2在LibriSpeech dev-clean上的预期指标：

- **WER (词错误率)**: 5-8%
- **CER (字符错误率)**: 2-4%
- **RTF (实时因子)**: 0.05x (GPU) 或 1.0x (CPU)

## 系统要求

### 必需
- Python 3.10+
- ffmpeg (音频处理)
- 约2GB磁盘空间

### 推荐
- NVIDIA GPU with CUDA (用于快速评估)
- 4GB+ RAM
- 良好的网络连接(用于下载)

## 故障排除

### 下载失败
```bash
# 尝试手动下载
wget https://www.openslr.org/resources/12/dev-clean.tar.gz
tar -xzf dev-clean.tar.gz -C test_data/
```

### ffmpeg未安装
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg
```

### GPU内存不足
```bash
# 使用CPU或减小chunk size
python3 evaluate_asr.py ... --device cpu
python3 evaluate_asr.py ... --chunk-duration 15
```

## 批量评估

创建并运行批量评估脚本：

```bash
# 评估所有样本
for sample in short medium long xlarge 2hours; do
    python3 evaluate_asr.py \
        --audio test_data/audio_${sample}.wav \
        --reference test_data/reference_${sample}.txt \
        --output results_${sample}.json \
        --device cuda
done

# 查看所有结果
for sample in short medium long xlarge 2hours; do
    wer=$(jq -r '.metrics.wer' results_${sample}.json)
    echo "$sample: WER=${wer}%"
done
```

## 高级用法

### 创建自定义时长

修改 `process_librispeech.py` 中的 `target_durations` 列表。

### 使用其他LibriSpeech子集

```bash
# 下载其他子集
wget https://www.openslr.org/resources/12/test-clean.tar.gz
tar -xzf test-clean.tar.gz -C test_data/

# 重新处理
python3 process_librispeech.py
```

### 选择特定说话人

修改 `process_librispeech.py` 添加过滤逻辑。

## 相关文档

- **LIBRISPEECH_GUIDE.md** - 完整详细的使用指南
- **EVALUATION_GUIDE.md** - ASR评估工具使用指南
- **TEST_DATA_GUIDE.md** - 测试数据准备通用指南
- **TESTING_SUMMARY.md** - 项目总体概览

## LibriSpeech数据集信息

- **官网**: https://www.openslr.org/12/
- **论文**: "LibriSpeech: An ASR corpus based on public domain audio books" (2015)
- **许可**: CC BY 4.0
- **引用**:
  ```
  @inproceedings{panayotov2015librispeech,
    title={Librispeech: an ASR corpus based on public domain audio books},
    author={Panayotov, Vassil and Chen, Guoguo and Povey, Daniel and Khudanpur, Sanjeev},
    booktitle={ICASSP},
    year={2015}
  }
  ```

## 支持

遇到问题？

1. 查看 **LIBRISPEECH_GUIDE.md** 中的故障排除章节
2. 确认系统满足要求
3. 检查网络连接（用于下载）
4. 验证ffmpeg已安装
5. 尝试使用较小的样本（short）进行测试

## 总结

LibriSpeech工具集提供了一个完整的解决方案，用于：
- ✅ 自动下载和处理LibriSpeech数据集
- ✅ 创建不同时长的测试音频（5分钟到2小时）
- ✅ 运行ASR准确率评估
- ✅ 生成详细的评估报告

**从零到完成评估只需一条命令：**
```bash
./quick_start_librispeech.sh
```
