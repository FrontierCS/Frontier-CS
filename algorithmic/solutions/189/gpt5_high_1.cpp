#include <bits/stdc++.h>
using namespace std;

struct FastOutput {
    static const size_t SZ = 1 << 20; // 1MB buffer
    char buf[SZ];
    size_t pos;
    FastOutput() : pos(0) {}
    ~FastOutput() { flush(); }
    inline void flush() {
        if (pos) {
            fwrite(buf, 1, pos, stdout);
            pos = 0;
        }
    }
    inline void push(char c) {
        if (pos == SZ) flush();
        buf[pos++] = c;
    }
    inline void repeat(char c, size_t cnt) {
        while (cnt) {
            if (pos == SZ) flush();
            size_t space = SZ - pos;
            size_t tofill = cnt < space ? cnt : space;
            memset(buf + pos, c, tofill);
            pos += tofill;
            cnt -= tofill;
        }
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s1, s2;
    if (!getline(cin, s1)) s1 = "";
    if (!getline(cin, s2)) s2 = "";
    size_t n = s1.size(), m = s2.size();

    FastOutput out;
    size_t i = 0, j = 0;

    while (i < n && j < m) {
        if (s1[i] == s2[j]) {
            // Emit a run of 'M' for consecutive matches
            size_t startI = i, startJ = j;
            size_t run = 0;
            while (i < n && j < m && s1[i] == s2[j]) {
                ++i; ++j; ++run;
            }
            out.repeat('M', run);
            continue;
        }

        // Heuristic: handle single-character insertions/deletions
        if (j + 1 < m && s1[i] == s2[j + 1]) {
            out.push('I');
            ++j;
            continue;
        }
        if (i + 1 < n && s1[i + 1] == s2[j]) {
            out.push('D');
            ++i;
            continue;
        }

        // Default: substitute
        out.push('M');
        ++i; ++j;
    }

    if (i < n) out.repeat('D', n - i);
    if (j < m) out.repeat('I', m - j);
    out.push('\n');
    return 0;
}