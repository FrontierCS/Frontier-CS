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

    inline bool isSpace(char c) {
        return c == ' ' || c == '\n' || c == '\r' || c == '\t' || c == '\f' || c == '\v';
    }

    bool skipBlanks() {
        char c;
        do {
            c = getChar();
            if (!c) return false;
        } while (isSpace(c));
        idx--; // put back one non-space
        return true;
    }

    bool nextLong(long long &out) {
        if (!skipBlanks()) return false;
        char c = getChar();
        bool neg = false;
        if (c == '-') {
            neg = true;
            c = getChar();
        }
        long long x = 0;
        while (c >= '0' && c <= '9') {
            x = x * 10 + (c - '0');
            c = getChar();
        }
        out = neg ? -x : x;
        return true;
    }

    bool nextStr(string &s) {
        if (!skipBlanks()) return false;
        s.clear();
        char c = getChar();
        while (c && !isSpace(c)) {
            s.push_back(c);
            c = getChar();
        }
        return true;
    }
};

struct FastOutput {
    static const int BUFSIZE = 1 << 20;
    int idx;
    char buf[BUFSIZE];

    FastOutput() : idx(0) {}

    ~FastOutput() {
        flush();
    }

    inline void flush() {
        if (idx) {
            fwrite(buf, 1, idx, stdout);
            idx = 0;
        }
    }

    inline void putChar(char c) {
        if (idx >= BUFSIZE) flush();
        buf[idx++] = c;
    }

    inline void writeLong(long long x) {
        if (x == 0) {
            putChar('0');
            return;
        }
        if (x < 0) {
            putChar('-');
            x = -x;
        }
        char s[24];
        int n = 0;
        while (x > 0) {
            s[n++] = char('0' + (x % 10));
            x /= 10;
        }
        for (int i = n - 1; i >= 0; --i)
            putChar(s[i]);
    }
};

int main() {
    FastScanner fs;
    FastOutput fo;

    long long n, m, k;
    string epsStr;

    if (!fs.nextLong(n)) return 0;
    fs.nextLong(m);
    fs.nextLong(k);
    fs.nextStr(epsStr); // eps not used, but read to consume input

    if (k <= 0) return 0;

    long long q = n / k;
    long long r = n % k;

    for (long long part = 1; part <= k; ++part) {
        long long sz = q + (part <= r ? 1 : 0);
        for (long long i = 0; i < sz; ++i) {
            fo.writeLong(part);
            fo.putChar(' ');
        }
    }
    fo.putChar('\n');
    fo.flush();
    return 0;
}