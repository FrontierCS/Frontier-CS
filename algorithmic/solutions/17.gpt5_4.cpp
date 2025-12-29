#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner() : idx(0), size(0) {}

    inline char getChar() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }

    bool readLongLong(long long &out) {
        out = 0;
        char c = getChar();
        while (c && c != '-' && (c < '0' || c > '9')) c = getChar();
        if (!c) return false;
        int sign = 1;
        if (c == '-') { sign = -1; c = getChar(); }
        long long val = 0;
        while (c && c >= '0' && c <= '9') {
            val = val * 10 + (c - '0');
            c = getChar();
        }
        out = val * sign;
        return true;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    vector<long long> raw;
    long long x;
    while (fs.readLongLong(x)) raw.push_back(x);
    if (raw.empty()) return 0;

    auto tryFormatWithT = [&](vector<long long>& a, vector<int>& answers) -> bool {
        size_t pos = 0;
        long long T = a[pos++];
        if (T <= 0) return false;
        size_t ntests = (size_t)T;
        size_t cur = pos;
        for (size_t t = 0; t < ntests; ++t) {
            if (cur >= a.size()) return false;
            long long n = a[cur++];
            if (n < 0) return false;
            if (cur + (size_t)n > a.size()) return false;
            cur += (size_t)n;
        }
        if (cur != a.size()) return false;

        answers.clear();
        cur = pos;
        for (size_t t = 0; t < ntests; ++t) {
            long long n = a[cur++];
            int ans = 0;
            for (int i = 0; i < n; ++i) {
                if ((long long)a[cur + i] == n) {
                    ans = i + 1;
                }
            }
            cur += (size_t)n;
            answers.push_back(ans);
        }
        return true;
    };

    vector<int> answers;
    if (!tryFormatWithT(raw, answers)) {
        // Try format without T: one or more test cases as [n, p1..pn]...
        size_t pos = 0;
        while (pos < raw.size()) {
            long long n = raw[pos++];
            if (n < 0) break;
            if (pos + (size_t)n > raw.size()) break;
            int ans = 0;
            for (int i = 0; i < n; ++i) {
                if ((long long)raw[pos + i] == n) ans = i + 1;
            }
            pos += (size_t)n;
            answers.push_back(ans);
        }
    }

    for (size_t i = 0; i < answers.size(); ++i) {
        if (i) cout << '\n';
        cout << answers[i];
    }
    return 0;
}