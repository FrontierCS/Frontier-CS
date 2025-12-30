#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner() : idx(0), size(0) {}
    inline char getChar() {
        if (idx >= size) {
            size = fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    bool readInt(int &out) {
        char c;
        int sign = 1;
        int x = 0;
        c = getChar();
        if (!c) return false;
        while (c != '-' && (c < '0' || c > '9')) {
            c = getChar();
            if (!c) return false;
        }
        if (c == '-') {
            sign = -1;
            c = getChar();
        }
        while (c >= '0' && c <= '9') {
            x = x * 10 + (c - '0');
            c = getChar();
        }
        out = x * sign;
        return true;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int n, m;
    if (!fs.readInt(n)) return 0;
    fs.readInt(m);

    vector<int> pos(n + 1, 0), neg(n + 1, 0);

    int a, b, c;
    for (int i = 0; i < m; ++i) {
        fs.readInt(a);
        fs.readInt(b);
        fs.readInt(c);
        if (a > 0) ++pos[a]; else ++neg[-a];
        if (b > 0) ++pos[b]; else ++neg[-b];
        if (c > 0) ++pos[c]; else ++neg[-c];
    }

    string out;
    out.reserve(n * 2 + 2);
    for (int i = 1; i <= n; ++i) {
        if (i > 1) out.push_back(' ');
        int val = (pos[i] >= neg[i]) ? 1 : 0;
        out.push_back(char('0' + val));
    }
    out.push_back('\n');
    cout << out;
    return 0;
}