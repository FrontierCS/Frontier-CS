#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, len;
    char buf[BUFSIZE];

    FastScanner() : idx(0), len(0) {}

    inline char getChar() {
        if (idx >= len) {
            len = fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (len == 0) return 0;
        }
        return buf[idx++];
    }

    inline bool skipBlanks() {
        char c;
        do {
            c = getChar();
            if (!c) return false;
        } while (c == ' ' || c == '\n' || c == '\r' || c == '\t' || c == '\v' || c == '\f');
        idx--;
        return true;
    }

    bool readInt(int &out) {
        if (!skipBlanks()) return false;
        int sign = 1;
        char c = getChar();
        if (c == '-') {
            sign = -1;
            c = getChar();
        } else if (c == '+') {
            c = getChar();
        }
        long long val = 0;
        while (c >= '0' && c <= '9') {
            val = val * 10 + (c - '0');
            c = getChar();
        }
        out = (int)(val * sign);
        return true;
    }

    bool readDouble(double &out) {
        if (!skipBlanks()) return false;
        int sign = 1;
        char c = getChar();
        if (c == '-') {
            sign = -1;
            c = getChar();
        } else if (c == '+') {
            c = getChar();
        }
        long double val = 0.0L;

        while (c >= '0' && c <= '9') {
            val = val * 10.0L + (c - '0');
            c = getChar();
        }

        if (c == '.') {
            long double frac = 0.0L, base = 1.0L;
            c = getChar();
            while (c >= '0' && c <= '9') {
                frac = frac * 10.0L + (c - '0');
                base *= 10.0L;
                c = getChar();
            }
            val += frac / base;
        }

        if (c == 'e' || c == 'E') {
            int esign = 1;
            int expv = 0;
            c = getChar();
            if (c == '-') {
                esign = -1;
                c = getChar();
            } else if (c == '+') {
                c = getChar();
            }
            while (c >= '0' && c <= '9') {
                expv = expv * 10 + (c - '0');
                c = getChar();
            }
            val *= powl(10.0L, (long double)(esign * expv));
        }

        out = (double)(val * sign);
        return true;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;

    int n;
    if (!fs.readInt(n)) return 0;

    vector<double> x(n + 1), y(n + 1);
    for (int i = 1; i <= n; ++i) {
        double xi, yi;
        fs.readDouble(xi);
        fs.readDouble(yi);
        x[i] = xi;
        y[i] = yi;
    }

    int m;
    fs.readInt(m);

    long double sumLen = 0.0L;
    for (int i = 0; i < m; ++i) {
        int a, b;
        fs.readInt(a);
        fs.readInt(b);
        double dx = x[a] - x[b];
        double dy = y[a] - y[b];
        sumLen += sqrt(dx * dx + dy * dy);
    }

    double r;
    fs.readDouble(r);

    double p1, p2, p3, p4;
    fs.readDouble(p1);
    fs.readDouble(p2);
    fs.readDouble(p3);
    fs.readDouble(p4);

    const long double PI = acosl(-1.0L);
    long double R = (long double)r;
    long double area = 2.0L * R * sumLen + (long double)m * PI * R * R;

    printf("%.7Lf\n", area);
    return 0;
}