# Wider container AI integration

The paired private deployment replaces native Lemonade inference with these local services:

| Capability | Container/runtime | Client |
|---|---|---|
| General chat / vision | llama.cpp router with the existing vision projector | Open WebUI |
| Coding | Same router, Coder-Next preset | Cline Plan/Act |
| Alternate local chat model | Same router, separate preset | OpenAI-compatible clients |
| Speech recognition | This tool's Whisper.cpp service | Portable companion and WebUI audio adapter |
| Spoken replies | Kokoro ONNX CPU service with existing voices | Open WebUI |

The CPU migration baseline uses one loaded large language model at a time. Endpoints are bound to loopback; model files are mounted read-only. Model files, credentials, local paths, backups and personal account/chat data are not published. The desktop input helper remains a Windows application.

Synthetic chat, vision, structured coding-tool calls, model switching and English/Spanish voice pipelines passed in containers. The full synthetic voice loop took about four seconds per tested language after the models were warm. These observations are not microphone, real-application, full-context, offline, reboot or second-host acceptance. AMD GPU/NPU acceleration is not claimed. Private operating details and exact source/image records belong in the paired workspace.
