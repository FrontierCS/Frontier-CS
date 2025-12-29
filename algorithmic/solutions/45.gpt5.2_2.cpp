#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr size_t BUFSIZE = 1 << 20;
    char buf[BUFSIZE];
    size_t idx = 0, size = 0;

    inline char readChar() {
        if (idx >= size) {
            size = fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }

    inline bool skipBlanks() {
        char c;
        do {
            c = readChar();
            if (!c) return false;
        } while (c <= ' ');
        idx--;
        return true;
    }

    template <class T>
    bool readInt(T &out) {
        if (!skipBlanks()) return false;
        char c = readChar();
        bool neg = false;
        if (c == '-') { neg = true; c = readChar(); }
        T val = 0;
        while (c > ' ') {
            val = val * 10 + (c - '0');
            c = readChar();
        }
        out = neg ? -val : val;
        return true;
    }

    bool readToken(string &s) {
        if (!skipBlanks()) return false;
        s.clear();
        char c = readChar();
        while (c > ' ') {
            s.push_back(c);
            c = readChar();
        }
        return true;
    }
};

struct FastOutput {
    static constexpr size_t BUFSIZE = 1 << 20;
    char buf[BUFSIZE];
    size_t idx = 0;

    ~FastOutput() { flush(); }

    inline void flush() {
        if (idx) {
            fwrite(buf, 1, idx, stdout);
            idx = 0;
        }
    }

    inline void pushChar(char c) {
        if (idx >= BUFSIZE) flush();
        buf[idx++] = c;
    }

    inline void writeInt(int x, char endc) {
        if (x == 0) {
            pushChar('0');
            pushChar(endc);
            return;
        }
        if (x < 0) {
            pushChar('-');
            x = -x;
        }
        char s[16];
        int n = 0;
        while (x) {
            s[n++] = char('0' + (x % 10));
            x /= 10;
        }
        while (n--) pushChar(s[n]);
        pushChar(endc);
    }
};

int main() {
    FastScanner fs;
    long long n, m;
    int k;
    string epsToken;

    if (!fs.readInt(n)) return 0;
    fs.readInt(m);
    fs.readInt(k);
    fs.readToken(epsToken); // eps not needed for this construction

    // Discard edges
    int u, v;
    for (long long i = 0; i < m; i++) {
        fs.readInt(u);
        fs.readInt(v);
    }

    FastOutput fo;
    for (long long i = 1; i <= n; i++) {
        int part = int((i - 1) % k) + 1;
        fo.writeInt(part, (i == n) ? '\n' : ' ');
    }
    fo.flush();
    return 0;
}