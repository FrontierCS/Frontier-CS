#include <bits/stdc++.h>
using namespace std;

class FastScanner {
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

public:
    template <class T>
    bool readInt(T &out) {
        char c;
        do {
            c = readChar();
            if (!c) return false;
        } while (c <= ' ');

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

    bool readDouble(double &out) {
        char c;
        do {
            c = readChar();
            if (!c) return false;
        } while (c <= ' ');

        bool neg = false;
        if (c == '-') { neg = true; c = readChar(); }

        long long ip = 0;
        while (c >= '0' && c <= '9') {
            ip = ip * 10 + (c - '0');
            c = readChar();
        }

        double val = (double)ip;
        if (c == '.') {
            double p = 1.0;
            c = readChar();
            while (c >= '0' && c <= '9') {
                p *= 0.1;
                val += (c - '0') * p;
                c = readChar();
            }
        }
        out = neg ? -val : val;
        return true;
    }
};

class FastOutput {
    static constexpr size_t BUFSIZE = 1 << 20;
    char buf[BUFSIZE];
    size_t idx = 0;

public:
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

    inline void writeInt(int x, char after) {
        if (x == 0) {
            pushChar('0');
            if (after) pushChar(after);
            return;
        }
        char s[16];
        int n = 0;
        while (x > 0) {
            s[n++] = char('0' + (x % 10));
            x /= 10;
        }
        while (n--) pushChar(s[n]);
        if (after) pushChar(after);
    }
};

int main() {
    FastScanner fs;
    long long n_ll, m_ll, k_ll;
    double eps;
    if (!fs.readInt(n_ll)) return 0;
    fs.readInt(m_ll);
    fs.readInt(k_ll);
    fs.readDouble(eps);

    int n = (int)n_ll;
    int k = (int)k_ll;

    // Balanced, contiguous block partition by vertex id.
    int ideal = (n + k - 1) / k;
    // cap exists but we don't need it because each block size <= ideal and cap >= ideal for eps>=0.
    // long double cap_ld = floor((1.0L + (long double)eps) * (long double)ideal + 1e-18L);

    FastOutput fo;
    for (int i = 1; i <= n; i++) {
        int part = (i - 1) / ideal + 1; // 1..k
        fo.writeInt(part, i == n ? '\n' : ' ');
    }
    fo.flush();
    return 0;
}