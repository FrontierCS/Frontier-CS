#include <bits/stdc++.h>
using namespace std;

struct FastOutput {
    static const size_t SZ = 1 << 20; // 1MB buffer
    char buf[SZ];
    size_t idx;
    FastOutput() : idx(0) {}
    ~FastOutput() { flush(); }
    inline void flush() {
        if (idx) {
            fwrite(buf, 1, idx, stdout);
            idx = 0;
        }
    }
    inline void push(char c) {
        if (idx == SZ) flush();
        buf[idx++] = c;
    }
    inline void writeRepeat(char c, size_t cnt) {
        // Write cnt copies of c
        while (cnt--) {
            if (idx == SZ) flush();
            buf[idx++] = c;
        }
    }
};

static inline size_t matchCount(const string& a, size_t ai, const string& b, size_t bi, size_t len) {
    const char* pa = a.data() + ai;
    const char* pb = b.data() + bi;
    size_t cnt = 0;
    for (size_t k = 0; k < len; ++k) cnt += (pa[k] == pb[k]);
    return cnt;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    string s1, s2;
    if (!(cin >> s1)) s1.clear();
    if (!(cin >> s2)) s2.clear();

    const size_t n = s1.size();
    const size_t m = s2.size();

    FastOutput out;

    size_t i = 0, j = 0;
    const size_t BLOCK = 2048;

    // Optional: quickly consume initial matching prefix to reduce comparisons
    while (i < n && j < m) {
        if (s1[i] == s2[j]) {
            out.push('M');
            ++i; ++j;
        } else {
            break;
        }
    }

    while (i < n && j < m) {
        size_t rem1 = n - i;
        size_t rem2 = m - j;
        size_t K0 = min(BLOCK, min(rem1, rem2));

        // Compute mismatches for keeping current alignment
        size_t score0 = matchCount(s1, i, s2, j, K0);
        size_t mism0 = K0 - score0;

        // Try insertion (advance j by 1 before block)
        size_t mismIns = numeric_limits<size_t>::max() / 4;
        if (j < m) {
            size_t rem2Ins = m - (j + 1);
            size_t Kins = min(BLOCK, min(rem1, rem2Ins));
            size_t scoreIns = (Kins > 0) ? matchCount(s1, i, s2, j + 1, Kins) : 0;
            mismIns = 1 + (Kins - scoreIns);
        }

        // Try deletion (advance i by 1 before block)
        size_t mismDel = numeric_limits<size_t>::max() / 4;
        if (i < n) {
            size_t rem1Del = n - (i + 1);
            size_t Kdel = min(BLOCK, min(rem1Del, rem2));
            size_t scoreDel = (Kdel > 0) ? matchCount(s1, i + 1, s2, j, Kdel) : 0;
            mismDel = 1 + (Kdel - scoreDel);
        }

        // Choose best option
        // Prefer keep on ties to reduce unnecessary I/D
        if (mismIns < mism0 && mismIns <= mismDel && j < m) {
            out.push('I');
            ++j;
        } else if (mismDel < mism0 && mismDel < mismIns && i < n) {
            out.push('D');
            ++i;
        }
        // After optional I/D, output a block of M's
        if (i >= n || j >= m) break;
        size_t L = min(BLOCK, min(n - i, m - j));
        out.writeRepeat('M', L);
        i += L;
        j += L;
    }

    // Tail handling
    if (i < n) out.writeRepeat('D', n - i);
    if (j < m) out.writeRepeat('I', m - j);

    out.push('\n');
    out.flush();
    return 0;
}