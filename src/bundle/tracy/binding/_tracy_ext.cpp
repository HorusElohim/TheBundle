// Copyright 2026 HorusElohim
//
// Licensed to the Apache Software Foundation (ASF) under one
// or more contributor license agreements.  See the NOTICE file
// distributed with this work for additional information
// regarding copyright ownership.  The ASF licenses this file
// to you under the Apache License, Version 2.0 (the
// "License"); you may not use this file except in compliance
// with the License.  You may obtain a copy of the License at
//
//   http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing,
// software distributed under the License is distributed on an
// "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
// KIND, either express or implied.  See the License for the
// specific language governing permissions and limitations
// under the License.

// TRACY_ENABLE must be defined before any Tracy header is included.
// It is passed via -DTRACY_ENABLE (or /DTRACY_ENABLE on MSVC) at compile time.
#include "tracy/Tracy.hpp"
#include "tracy/TracyC.h"
#include "client/TracyProfiler.hpp"
#include <pybind11/pybind11.h>

#include <memory>
#include <string>

namespace py = pybind11;

// Persistent source-location data for a Python call site.
//
// One instance is created per unique (file, line, qualname) triple and cached
// in Python's _srcloc_cache for the process lifetime.  The strings are owned
// by this struct; ScopedZone's transient constructor copies them into Tracy's
// queue, so there are no dangling-pointer risks on reuse.
struct SrcLoc {
    std::string source;
    std::string function;
    std::string name;
    uint32_t line;
    uint32_t color;

    SrcLoc(uint32_t line,
           std::string source, std::string function, std::string name,
           uint32_t color)
        : source(std::move(source))
        , function(std::move(function))
        , name(std::move(name))
        , line(line)
        , color(color) {}

    // Non-copyable: moving the strings would invalidate any future c_str()
    // pointers held by an in-flight zone_begin call.
    SrcLoc(const SrcLoc&) = delete;
    SrcLoc& operator=(const SrcLoc&) = delete;
};

// Active zone — owns a heap-allocated tracy::ScopedZone that lives from
// zone_begin to zone_end.
//
// tracy::ScopedZone's transient constructor (the overload that takes
// line/source/function/name strings) uses the dynamic/alloc variant
// internally: source-location data is embedded inline in the queue message,
// so no ServerQuerySourceLocation round-trips with tracy-capture are needed.
//
// The ScopedZone destructor emits zone_end to Tracy's queue.  We manage it
// via raw new/delete (matching the official Python bindings pattern in
// ScopedZone.hpp PyScopedZone::Enter / PyScopedZone::Exit).
struct ZoneCtx {
    tracy::ScopedZone* zone = nullptr;

    ZoneCtx() = default;

    // Non-copyable — the ScopedZone must not be moved after construction.
    ZoneCtx(const ZoneCtx&) = delete;
    ZoneCtx& operator=(const ZoneCtx&) = delete;

    void end() {
        if (zone) {
            delete zone;
            zone = nullptr;
        }
    }
};

PYBIND11_MODULE(_tracy_ext, m) {
    m.doc() = "Tracy profiler C extension for TheBundle";

    py::class_<ZoneCtx>(m, "ZoneCtx");
    py::class_<SrcLoc>(m, "SrcLoc");  // opaque — Python only stores references

    // Create a persistent source location for a Python call site.
    // Returns a SrcLoc object that may be cached and passed to zone_begin
    // as many times as needed.
    m.def(
        "alloc_srcloc",
        [](uint32_t line, const std::string& source, const std::string& function,
           const std::string& name, uint32_t color) -> std::unique_ptr<SrcLoc> {
            return std::make_unique<SrcLoc>(line, source, function, name, color);
        },
        py::arg("line") = 0,
        py::arg("source") = "python",
        py::arg("function") = "python",
        py::arg("name"),
        py::arg("color") = 0);

    // Begin a Tracy zone using a persistent SrcLoc.
    //
    // Creates a new tracy::ScopedZone (transient/alloc variant) on the heap.
    // The constructor emits zone_begin to Tracy's lock-free ring buffer.
    // Python receives a ZoneCtx that must be passed to zone_end.
    m.def("zone_begin", [](SrcLoc& srcloc) -> std::unique_ptr<ZoneCtx> {
        auto ctx = std::make_unique<ZoneCtx>();
        ctx->zone = new tracy::ScopedZone(
            srcloc.line,
            srcloc.source.c_str(),   srcloc.source.size(),
            srcloc.function.c_str(), srcloc.function.size(),
            srcloc.name.c_str(),     srcloc.name.size(),
            srcloc.color, -1, true);
        return ctx;
    });

    // End the zone opened by zone_begin.
    // Deletes the ScopedZone, whose destructor emits zone_end.
    m.def("zone_end", [](ZoneCtx& ctx) {
        ctx.end();
    });

    // Frame markers.
    m.def("frame_mark", []() {
        ___tracy_emit_frame_mark(nullptr);
    });

    m.def("frame_mark_named", [](const std::string& name) {
        ___tracy_emit_frame_mark(name.c_str());
    });

    // Live numeric plot in the viewer.
    m.def("plot", [](const std::string& name, double val) {
        ___tracy_emit_plot(name.c_str(), val);
    });

    // Text annotation on the timeline; optional ARGB color.
    m.def(
        "message",
        [](const std::string& text, uint32_t color) {
            if (color)
                ___tracy_emit_messageC(text.c_str(), text.size(), color, 0);
            else
                ___tracy_emit_message(text.c_str(), text.size(), 0);
        },
        py::arg("text"), py::arg("color") = 0);

    // Name the calling thread in the viewer.
    m.def("set_thread_name", [](const std::string& name) {
        ___tracy_set_thread_name(name.c_str());
    });

    // True when a Tracy viewer is connected.
    m.def("is_connected", []() -> bool {
        return ___tracy_connected() != 0;
    });

    // Request a clean profiler shutdown.
    // Releases the GIL while waiting so Python threads remain unblocked.
    m.def("shutdown", []() {
        tracy::GetProfiler().RequestShutdown();
    }, py::call_guard<py::gil_scoped_release>());
}
