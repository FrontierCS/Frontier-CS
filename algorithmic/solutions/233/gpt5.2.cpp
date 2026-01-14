#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr size_t BUFSIZE = 1 << 20;
    int idx = 0, size = 0;
    char buf[BUFSIZE];

    inline char readChar() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }

    template <class T>
    bool readInt(T &out) {
        char c;
        do {
            c = readChar();
            if (!c) return false;
        } while (c <= ' ');

        bool neg = false;
        if (c == '-') {
            neg = true;
            c = readChar();
        }

        T val = 0;
        while (c > ' ') {
            val = val * 10 + (c - '0');
            c = readChar();
        }
        out = neg ? -val : val;
        return true;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;

    int t;
    if (!fs.readInt(t)) return 0;

    while (t--) {
        int n;
        int m;
        fs.readInt(n);
        fs.readInt(m);

        for (int i = 0; i < n * n; i++) {
            int x;
            fs.readInt(x);
        }

        long long total = 1LL * n * (2LL * n - 1);
        vector<int> vals;
        vals.reserve((size_t)total);
        for (long long i = 0; i < total; i++) {
            int x;
            fs.readInt(x);
            vals.push_back(x);
        }

        if (m < (int)vals.size()) {
            nth_element(vals.begin(), vals.begin() + m, vals.end());
            vals.resize(m);
        }
        sort(vals.begin(), vals.end());

        cout << "!";
        for (int i = 0; i < m; i++) {
            cout << ' ' << vals[i];
        }
        cout << '\n';
    }
    return 0;
}