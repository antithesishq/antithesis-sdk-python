from cffi import FFI

CDEF='''\
uint64_t fuzz_get_random();
void fuzz_json_data(const char* message, size_t length);
void fuzz_flush();
size_t init_coverage_module(size_t edge_count, const char* symbol_file_name);
bool notify_coverage(size_t edge_plus_module);
'''

SRC="""
#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>

#ifdef __cplusplus
extern \"C\" {
#endif

uint64_t fuzz_get_random();
void fuzz_json_data( const char* message, size_t length );
void fuzz_flush();
size_t init_coverage_module(size_t edge_count, const char* symbol_file_name);
bool notify_coverage(size_t edge_plus_module);

#ifdef __cplusplus
}
#endif

void fuzz_flush() {
fwrite(\"Flushed\", 1, 7, stdout);
fwrite(\"\\n\", 1, 1, stdout);
}

uint64_t fuzz_get_random() {
    return 213;
}

void fuzz_json_data( const char* message, size_t length ) {
    fwrite(\"JSONOUT\", 1, 7, stdout);
    fwrite(\"\\n\", 1, 1, stdout);
}

size_t init_coverage_module(size_t edge_count, const char* symbol_file_name) {
    return 0;
}

bool notify_coverage(size_t edge_plus_module) {
    return true;
};

"""


ffibuilder = FFI()
ffibuilder.cdef(CDEF)
ffibuilder.set_source( '_voidstar', SRC)
if __name__ == '__main__':
    ffibuilder.compile()
