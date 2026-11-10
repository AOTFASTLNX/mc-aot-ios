# mc-aot-ios — iOS AOT 流水线实验台

这是一个**只含 CI 编排**的仓库：公开代码只有 workflow 和编排脚本，不含任何游戏内容、第三方私有源码或凭据。

用途：在 GitHub 托管的 macOS runner 上验证并运行「GraalVM Native Image → iOS arm64 原生二进制」的构建流程（免 Java JIT）。上游工程通过仓库 secret `MCFAO_TOKEN` 在运行时拉取，不落库。

- `.github/workflows/probe.yml` — runner 能力探针（Xcode/SDK/模拟器/内存/网络）
- 构建产物不上传到公开 Release；只作为 Actions artifact 保留。
