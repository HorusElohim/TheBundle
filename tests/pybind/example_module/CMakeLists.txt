cmake_minimum_required(VERSION 3.20)

project(example_module
    VERSION 1.0
    DESCRIPTION "Example Library"
    LANGUAGES CXX
)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
# Enable generation of position-independent code (e.g., -fPIC) for all targets by default.
# Required for building shared libraries and for compatibility with ASLR.
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Set minimum macOS deployment target for std::variant support
if(APPLE)
    set(CMAKE_OSX_DEPLOYMENT_TARGET "10.9" CACHE STRING "Minimum OS X deployment version")
endif()

# Collect all .cpp sources
file(GLOB_RECURSE sources src/*.cpp)
add_library(${PROJECT_NAME} ${sources})

# Add the include directory for the export.h file
target_include_directories(${PROJECT_NAME} PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)

# PkgConfig generation
set(INPUT_PKG_FILE ${CMAKE_CURRENT_SOURCE_DIR}/cmake/${PROJECT_NAME}.pc.in)
set(OUTPUT_PKG_FILE ${CMAKE_CURRENT_BINARY_DIR}/${PROJECT_NAME}.pc)
configure_file(${INPUT_PKG_FILE} ${OUTPUT_PKG_FILE} @ONLY)

include(GNUInstallDirs)
install(TARGETS ${PROJECT_NAME}
    EXPORT ${PROJECT_NAME}Targets
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)
install(DIRECTORY include/ DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
install(FILES ${OUTPUT_PKG_FILE} DESTINATION ${CMAKE_INSTALL_LIBDIR}/pkgconfig)
install(EXPORT ${PROJECT_NAME}Targets
    FILE ${PROJECT_NAME}Targets.cmake
    NAMESPACE ${PROJECT_NAME}::
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/${PROJECT_NAME}
)
