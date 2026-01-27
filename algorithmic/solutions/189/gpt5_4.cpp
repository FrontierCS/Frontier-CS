#include <bits/stdc++.h>
using namespace std;

struct FastOutput {
    static constexpr size_t BUFSIZE = 1 << 20; // 1MB
    vector<char> buf;
    FastOutput() { buf.reserve(BUFSIZE); }
    inline void push(char c) {
        buf.push_back(c);
        if (buf.size() >= BUFSIZE) flush();
    }
    inline void pushRepeat(char c, size_t cnt) {
        while (cnt) {
            if (buf.size() == BUFSIZE) flush();
            size_t space = BUFSIZE - buf.size();
            size_t batch = (cnt < space) ? cnt : space;
            buf.insert(buf.end(), batch, c);
            cnt -= batch;
        }
    }
    inline void flush() {
        if (!buf.empty()) {
            fwrite(buf.data(), 1, buf.size(), stdout);
            buf.clear();
        }
    }
    ~FastOutput() { flush(); }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s1, s2;
    if (!getline(cin, s1)) return 0;
    if (!getline(cin, s2)) s2 = "";

    size_t n = s1.size(), m = s2.size();
    size_t i = 0, j = 0;

    FastOutput out;

    while (i < n && j < m) {
        if (s1[i] == s2[j]) {
            size_t i0 = i, j0 = j;
            while (i < n && j < m && s1[i] == s2[j]) { ++i; ++j; }
            out.pushRepeat('M', i - i0);
        } else {
            bool del = (i + 1 < n && s1[i + 1] == s2[j]);
            bool ins = (j + 1 < m && s1[i] == s2[j + 1]);
            if (del && !ins) {
                out.push('D'); ++i;
            } else if (ins && !del) {
                out.push('I'); ++j;
            } else if (del && ins) {
                // Tie-break with small lookahead
                const int W = 4;
                int dlen = 0, ilen = 0;
                size_t ii = i + 1, jj = j;
                while (dlen < W && ii < n && jj < m && s1[ii] == s2[jj]) { ++dlen; ++ii; ++jj; }
                ii = i; jj = j + 1;
                while (ilen < W && ii < n && jj < m && s1[ii] == s2[jj]) { ++ilen; ++ii; ++jj; }
                if (dlen > ilen + 1) { out.push('D'); ++i; }
                else if (ilen > dlen + 1) { out.push('I'); ++j; }
                else { out.push('M'); ++i; ++j; }
            } else {
                out.push('M'); ++i; ++j;
            }
        }
    }
    if (i < n) out.pushRepeat('D', n - i);
    if (j < m) out.pushRepeat('I', m - j);

    out.flush();
    return 0;
}