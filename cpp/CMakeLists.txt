cmake_minimum_required(VERSION 3.15)
project(simorgh LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(simorgh
    src/bitboard.cpp
    src/book.cpp
    src/evaluate.cpp
    src/movegen.cpp
    src/notation.cpp
    src/position.cpp
    src/search.cpp
    src/stats.cpp
    src/tune.cpp
    src/uci.cpp
    src/main.cpp
)

if(MSVC)
    target_compile_options(simorgh PRIVATE /O2 /EHsc)
else()
    target_compile_options(simorgh PRIVATE -O2)
    # Link the runtime statically. Without this the exe resolves
    # libstdc++-6.dll from whatever happens to be first on PATH -- on a
    # machine with Git for Windows installed that is Git's own MinGW
    # runtime, and constructing an std::ifstream against the wrong one
    # segfaults. It also makes the binary standalone, which an engine
    # people copy around should be anyway.
    target_link_options(simorgh PRIVATE -static -static-libgcc -static-libstdc++)
endif()
