#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner(): idx(0), size(0) {}
    inline char getch() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    bool readInt(int &out) {
        char c; int sgn = 1; int x = 0;
        do {
            c = getch();
            if (!c) return false;
        } while (c <= ' ');
        if (c == '-') { sgn = -1; c = getch(); }
        for (; c >= '0' && c <= '9'; c = getch()) x = x * 10 + (c - '0');
        out = x * sgn;
        return true;
    }
} in;

struct FastWriter {
    static const int BUFSIZE = 1 << 20;
    int idx;
    char buf[BUFSIZE];
    FastWriter(): idx(0) {}
    ~FastWriter() { flush(); }
    inline void pushChar(char c) {
        if (idx >= BUFSIZE) flush();
        buf[idx++] = c;
    }
    inline void writeInt01(int x) {
        pushChar(char('0' + (x & 1)));
    }
    inline void writeSpace() { pushChar(' '); }
    inline void writeNL() { pushChar('\n'); }
    inline void flush() {
        if (idx) {
            fwrite(buf, 1, idx, stdout);
            idx = 0;
        }
    }
} out;

static uint64_t rng_state = 0x9e3779b97f4a7c15ull;
static inline uint64_t rng64() {
    rng_state ^= rng_state << 7;
    rng_state ^= rng_state >> 9;
    return rng_state;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!in.readInt(n)) return 0;
    in.readInt(m);

    // Handle m == 0 quickly
    if (m == 0) {
        for (int i = 1; i <= n; ++i) {
            out.writeInt01(0);
            if (i < n) out.writeSpace();
        }
        out.writeNL();
        out.flush();
        return 0;
    }

    // Seed RNG
    uint64_t seed = chrono::steady_clock::now().time_since_epoch().count();
    rng_state ^= seed ^ (seed << 13) ^ (seed >> 7);

    // Allocate arrays
    const int M3 = m * 3;
    int *lits = (int*)malloc(sizeof(int) * (size_t)M3);
    if (!lits) return 0;

    vector<int> posCount(n + 1, 0), negCount(n + 1, 0), occCount(n + 1, 0);

    // Read clauses and count occurrences
    for (int i = 0; i < m; ++i) {
        for (int k = 0; k < 3; ++k) {
            int v;
            in.readInt(v);
            lits[3*i + k] = v;
            int id = v > 0 ? v : -v;
            if (v > 0) posCount[id]++; else negCount[id]++;
            occCount[id]++;
        }
    }

    // Build adjacency offsets
    vector<int> start(n + 2, 0);
    for (int v = 1; v <= n; ++v) start[v + 1] = start[v] + occCount[v];
    // Fill adjacency list indices (occurrence indices)
    int *occIndex = (int*)malloc(sizeof(int) * (size_t)M3);
    if (!occIndex) return 0;
    vector<int> nextPos(n + 1);
    for (int v = 1; v <= n; ++v) nextPos[v] = start[v];
    for (int idx = 0; idx < M3; ++idx) {
        int lit = lits[idx];
        int v = lit > 0 ? lit : -lit;
        occIndex[nextPos[v]++] = idx;
    }

    // Initial assignment using majority (tie broken randomly)
    vector<unsigned char> x(n + 1, 0);
    for (int v = 1; v <= n; ++v) {
        if (posCount[v] > negCount[v]) x[v] = 1;
        else if (posCount[v] < negCount[v]) x[v] = 0;
        else x[v] = (unsigned char)(rng64() & 1);
    }

    // Compute initial clause true counts
    unsigned char *clsTrueCnt = (unsigned char*)malloc(sizeof(unsigned char) * (size_t)m);
    if (!clsTrueCnt) return 0;
    for (int c = 0; c < m; ++c) {
        int base = 3 * c;
        int t = 0;
        int l0 = lits[base], v0 = l0 > 0 ? l0 : -l0;
        if ((l0 > 0) ? x[v0] : !x[v0]) ++t;
        int l1 = lits[base + 1], v1 = l1 > 0 ? l1 : -l1;
        if ((l1 > 0) ? x[v1] : !x[v1]) ++t;
        int l2 = lits[base + 2], v2 = l2 > 0 ? l2 : -l2;
        if ((l2 > 0) ? x[v2] : !x[v2]) ++t;
        clsTrueCnt[c] = (unsigned char)t;
    }

    // Greedy improvement passes
    const int PASSES = 2;
    for (int pass = 0; pass < PASSES; ++pass) {
        bool flipped_any = false;
        for (int v = 1; v <= n; ++v) {
            int s = start[v], e = start[v + 1];
            int gain = 0;
            for (int p = s; p < e; ++p) {
                int idx = occIndex[p];
                int c = idx / 3;
                int lit = lits[idx];
                unsigned char t = clsTrueCnt[c];
                bool litTrue = (lit > 0) ? (x[v] != 0) : (x[v] == 0);
                if (litTrue) {
                    if (t == 1) gain -= 1;
                } else {
                    if (t == 0) gain += 1;
                }
            }
            if (gain > 0) {
                flipped_any = true;
                unsigned char prev = x[v];
                x[v] ^= 1;
                for (int p = s; p < e; ++p) {
                    int idx = occIndex[p];
                    int c = idx / 3;
                    int lit = lits[idx];
                    bool wasTrue = (lit > 0) ? (prev != 0) : (prev == 0);
                    if (wasTrue) clsTrueCnt[c]--;
                    else clsTrueCnt[c]++;
                }
            }
        }
        if (!flipped_any) break;
    }

    // Output assignment
    for (int i = 1; i <= n; ++i) {
        out.writeInt01((int)x[i]);
        if (i < n) out.writeSpace();
    }
    out.writeNL();
    out.flush();

    free(lits);
    free(occIndex);
    free(clsTrueCnt);
    return 0;
}