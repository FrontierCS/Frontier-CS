#include <bits/stdc++.h>
using namespace std;

#ifndef _WIN32
#define GETCHAR getchar_unlocked
#else
#define GETCHAR getchar
#endif

inline bool readInt(int &out) {
    int c = GETCHAR();
    if (c == EOF) return false;
    int sign = 1;
    while (c != '-' && (c < '0' || c > '9')) {
        c = GETCHAR();
        if (c == EOF) return false;
    }
    if (c == '-') {
        sign = -1;
        c = GETCHAR();
    }
    int x = 0;
    while (c >= '0' && c <= '9') {
        x = x * 10 + (c - '0');
        c = GETCHAR();
    }
    out = x * sign;
    return true;
}

int main() {
    int n, m;
    if (!readInt(n)) return 0;
    readInt(m);

    vector<int> pos(n + 1, 0), neg(n + 1, 0);

    int a, b, c;
    for (int i = 0; i < m; ++i) {
        readInt(a); readInt(b); readInt(c);
        if (a > 0) ++pos[a]; else ++neg[-a];
        if (b > 0) ++pos[b]; else ++neg[-b];
        if (c > 0) ++pos[c]; else ++neg[-c];
    }

    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << (pos[i] >= neg[i] ? 1 : 0);
    }
    cout << '\n';
    return 0;
}