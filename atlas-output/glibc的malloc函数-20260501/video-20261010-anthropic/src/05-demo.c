/* Teaching demo, not glibc implementation.
 * Request sizes are candidates. Cache state and tunables select actual paths.
 * Linux/glibc: cc -O0 -g -o demo src/05-demo.c
 *             strace -e trace=brk,mmap,munmap ./demo
 * Startup mappings and physical-page faults are separate from malloc routing.
 */
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int allocation_round(size_t bytes, unsigned char value)
{
    unsigned char *p = malloc(bytes);
    if (p == NULL)
        return 1;
    memset(p, value, bytes);  /* Touch allocated bytes before returning them. */
    volatile unsigned char observed = p[bytes - 1];
    (void)observed;
    free(p);
    return 0;
}

int main(void)
{
    static const char small[] = "[candidate] 24-byte repeated reuse\n";
    static const char medium[] = "[candidate] 8192-byte arena-managed request\n";
    static const char large[] = "[candidate] 204800-byte large request\n";
    if (write(STDOUT_FILENO, small, sizeof small - 1) < 0)
        return 2;
    for (unsigned int i = 0; i < 8; ++i)
        if (allocation_round(24, (unsigned char)i))
            return 1;
    if (write(STDOUT_FILENO, medium, sizeof medium - 1) < 0)
        return 2;
    if (allocation_round(8192, 42))
        return 1;
    if (write(STDOUT_FILENO, large, sizeof large - 1) < 0)
        return 2;
    return allocation_round(204800, 43);
}
