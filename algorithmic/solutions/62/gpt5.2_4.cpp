#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr int BUFSIZE = 1 << 20;
    int idx = 0, size = 0;
    unsigned char buf[BUFSIZE];

    inline unsigned char read() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }

    template <class T>
    bool readInt(T &out) {
        unsigned char c;
        do {
            c = read();
            if (!c) return false;
        } while (c <= ' ');
        T sign = 1;
        if (c == '-') {
            sign = -1;
            c = read();
        }
        T val = 0;
        while (c > ' ') {
            val = val * 10 + (c - '0');
            c = read();
        }
        out = val * sign;
        return true;
    }
};

struct FastOutput {
    static constexpr int BUFSIZE = 1 << 20;
    int idx = 0;
    char buf[BUFSIZE];

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

    inline void writeInt(long long x) {
        if (x == 0) {
            pushChar('0');
            return;
        }
        if (x < 0) {
            pushChar('-');
            x = -x;
        }
        char s[24];
        int n = 0;
        while (x) {
            s[n++] = char('0' + (x % 10));
            x /= 10;
        }
        while (n--) pushChar(s[n]);
    }
};

struct Solver {
    int n, m, B, N;
    vector<vector<int>> st;
    vector<int> sz;
    vector<int> cnt; // flat: cnt[p*N + color]
    vector<uint64_t> ops;

    vector<int> avail;
    vector<int> pos;
    int ptr = 0;

    inline int &C(int p, int color) { return cnt[p * N + color]; }

    inline void addAvail(int i) {
        if (pos[i] == -1) {
            pos[i] = (int)avail.size();
            avail.push_back(i);
        }
    }

    inline void remAvail(int i) {
        int pi = pos[i];
        if (pi == -1) return;
        int last = avail.back();
        avail[pi] = last;
        pos[last] = pi;
        avail.pop_back();
        pos[i] = -1;
        if (ptr > (int)avail.size()) ptr = 0;
        if (ptr == (int)avail.size()) ptr = 0;
    }

    inline void doMove(int x, int y) {
        int oldX = sz[x], oldY = sz[y];
        int ball = st[x].back();
        st[x].pop_back();
        st[y].push_back(ball);
        --C(x, ball);
        ++C(y, ball);
        --sz[x];
        ++sz[y];
        if (oldX == m) addAvail(x);          // became non-full
        if (oldY == m - 1) remAvail(y);      // became full
        ops.push_back((uint64_t(x) << 32) | uint32_t(y));
    }

    inline int getDest(int start, int ex1, int ex2, bool avoidB) {
        int s = (int)avail.size();
        for (int k = 0; k < s; k++) {
            if (ptr >= s) ptr = 0;
            int v = avail[ptr++];
            if (v < start) continue;
            if (v == ex1 || v == ex2) continue;
            if (avoidB && v == B) continue;
            return v;
        }
        return -1;
    }

    inline int findR(int start, int p) {
        for (int i = start; i <= n + 1; i++) {
            if (i != p && i != B) return i;
        }
        return -1;
    }

    inline int chooseP(int start, int color) {
        for (int i = start; i <= n; i++) {
            if (C(i, color) > 0 && sz[i] > 0 && st[i].back() == color) return i;
        }
        for (int i = start; i <= n; i++) {
            if (C(i, color) > 0) return i;
        }
        return -1;
    }

    inline void collectTop(int p, int start, int color, int &collected) {
        // Precondition: st[p].back() == color
        while (sz[B] > collected) {
            int dest = getDest(start, B, p, true);
            if (dest != -1) {
                doMove(B, dest);
            } else {
                int r = findR(start, p);
                doMove(r, B);
                doMove(p, r);
                while (sz[B] > collected) doMove(B, p);
                doMove(r, B);
                ++collected;
                return;
            }
        }
        doMove(p, B);
        ++collected;
    }

    void solve() {
        if (n == 1 || m == 1) return;

        for (int color = 1; color <= n - 1; color++) {
            int start = color;
            int collected = 0;

            while (collected < m) {
                int p = chooseP(start, color);

                while (st[p].back() != color) {
                    int dest = getDest(start, p, -1, true);
                    if (dest == -1) dest = getDest(start, p, -1, false);
                    doMove(p, dest);
                }
                collectTop(p, start, color, collected);
            }

            int t = color;
            while (sz[t] > 0) {
                int dest = getDest(start, t, B, true);
                if (dest == -1) dest = getDest(start, t, B, false);
                doMove(t, dest);
            }
            for (int i = 0; i < m; i++) doMove(B, t);
        }

        while (sz[B] > 0) doMove(B, n);
    }
};

int main() {
    FastScanner fs;
    int n, m;
    if (!fs.readInt(n)) return 0;
    fs.readInt(m);

    // Read input always; for trivial cases output 0
    if (n == 1 || m == 1) {
        int x;
        for (int i = 0; i < n * m; i++) fs.readInt(x);
        FastOutput out;
        out.writeInt(0);
        out.pushChar('\n');
        return 0;
    }

    Solver s;
    s.n = n;
    s.m = m;
    s.B = n + 1;
    s.N = n + 2;

    s.st.assign(n + 2, {});
    s.sz.assign(n + 2, 0);
    s.cnt.assign((n + 2) * (n + 2), 0);

    for (int i = 1; i <= n; i++) {
        s.st[i].reserve(m);
        for (int j = 0; j < m; j++) {
            int c;
            fs.readInt(c);
            s.st[i].push_back(c);
            s.cnt[i * s.N + c]++;
        }
        s.sz[i] = m;
    }
    s.st[s.B].reserve(m);
    s.sz[s.B] = 0;

    s.pos.assign(n + 2, -1);
    s.avail.clear();
    s.addAvail(s.B);

    s.ops.reserve(1000000);

    s.solve();

    FastOutput out;
    out.writeInt((long long)s.ops.size());
    out.pushChar('\n');
    for (uint64_t op : s.ops) {
        uint32_t x = (uint32_t)(op >> 32);
        uint32_t y = (uint32_t)(op & 0xffffffffu);
        out.writeInt((int)x);
        out.pushChar(' ');
        out.writeInt((int)y);
        out.pushChar('\n');
    }
    out.flush();
    return 0;
}