# ADR-001: Retrieval Pipeline Refactoring

- Status: Accepted
- Date: 2026-08-29
- Scope: D15 – D16
- Authors: O-AI Engineering

---

# Context

KnowledgeAnswerService มีความรับผิดชอบหลายด้านในคลาสเดียว ได้แก่

- Intent Analysis
- Retrieval Planning
- Repository Search
- Evidence Ranking
- Conflict Detection
- Context Building
- Prompt Generation
- Response Generation

ทำให้

- Service มีขนาดใหญ่
- Retrieval Logic ซ้ำกับ Pipeline
- ทดสอบและบำรุงรักษายาก
- เพิ่ม Pipeline ใหม่ได้ยาก

จึงเริ่มโครงการ Refactoring ใน D15–D16

---

# Decision

เลือกใช้สถาปัตยกรรมแบบ Pipeline

```
KnowledgeAnswerService
        │
        ▼
RetrievalPipeline
        │
        ▼
ExecutionContext
```

โดยกำหนดให้

- RetrievalPipeline เป็นเจ้าของ Retrieval Logic
- KnowledgeAnswerService เป็น Application Service
- ExecutionContext เป็นตัวกลางในการแลกเปลี่ยนข้อมูล

---

# Design Principles

## 1. Single Responsibility

แบ่ง Retrieval ออกจาก Service

เดิม

```
KnowledgeAnswerService

├── _retrieve_records()
├── _build_evidence()
├── Prompt
├── Chat
└── Response
```

ใหม่

```
KnowledgeAnswerService

├── Orchestration
├── Prompt
├── Chat
└── Response

RetrievalPipeline

├── Retrieve
└── Build Evidence
```

---

## 2. ExecutionContext First

Pipeline ทุกตัว

- อ่านข้อมูลจาก ExecutionContext

และ

- เขียนผลกลับเข้า ExecutionContext

Service อ่านข้อมูลจาก ExecutionContext เท่านั้น

ไม่ควรสร้างข้อมูลเอง

---

## 3. Incremental Refactoring

ทุกการเปลี่ยนแปลงใช้ลำดับเดียวกัน

```
Audit

↓

Extract

↓

Bridge

↓

Switch

↓

Regression

↓

Delete
```

ห้าม

```
Delete

↓

Fix
```

---

## 4. Public API Stability

KnowledgeAnswerService เป็น Public API

Constructor ควรเปลี่ยนให้น้อยที่สุด

Dependency ใหม่

- RetrievalPipeline
- KnowledgeOrchestrator

เพิ่มแบบ Optional

เพื่อรักษา Backward Compatibility

---

## 5. Regression Driven Refactoring

ทุก Commit

ต้องผ่าน Regression ก่อน

ไม่มี Exception

Baseline

```
395 passed
4 skipped
```

ถือเป็น Quality Gate

---

# D15 Summary

Completed

- RetrievalComponents
- Dependency Bundle
- RetrievalPipeline Composition
- PipelineOrchestrator
- Runtime Preparation

Regression

```
395 passed
4 skipped
```

---

# D16 Summary

Completed

- _read_knowledge()
- _write_knowledge()
- RetrievalPipeline Runtime Activation
- Runtime Bridge

Regression

```
395 passed
4 skipped
```

---

# Deferred Decisions

ยังไม่ดำเนินการ

- ลบ Legacy Retrieval
- Test Builder
- Test Migration

เหตุผล

Legacy ยังมี Caller

```
KnowledgeAnswerService

↓

_retrieve_records()

↓

_build_evidence()
```

Delete จะทำเมื่อ

Caller = 0

---

# Lessons Learned

## สิ่งที่ได้ผล

✓ Audit ก่อน Refactor

✓ Regression ทุก Commit

✓ Bridge ก่อน Switch

✓ Public API Stable

✓ ExecutionContext เป็นศูนย์กลาง

---

## สิ่งที่ควรหลีกเลี่ยง

✗ ออกแบบ Builder ก่อนเห็นการใช้งานจริง

✗ เปลี่ยน Public Constructor โดยไม่จำเป็น

✗ ลบโค้ดก่อน Caller เป็นศูนย์

✗ Refactor หลาย Responsibility ใน Commit เดียว

---

# Future Work

เมื่อ Test Infrastructure พร้อม

ดำเนินการ

1. Test Migration

2. Remove Legacy Retrieval

3. Cleanup KnowledgeAnswerService

4. Freeze Retrieval Architecture

---

# Final Architecture

```
KnowledgeAnswerService
        │
        ▼
KnowledgeOrchestrator
        │
        ▼
Pipeline
        │
        ▼
RetrievalPipeline
        │
        ▼
ExecutionContext
```

---

# Status

Accepted

ถือเป็น Architecture Baseline สำหรับการพัฒนา Retrieval ของ O-AI ตั้งแต่ D16 เป็นต้นไป