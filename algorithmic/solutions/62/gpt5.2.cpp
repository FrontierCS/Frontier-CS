#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr size_t BUFSZ = 1 << 20;
    char buf[BUFSZ];
    size_t pos = 0, len = 0;

    inline char readChar() {
        if (pos >= len) {
            len = fread(buf, 1, BUFSZ, stdin);
            pos = 0;
            if (len == 0) return 0;
        }
        return buf[pos++];
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

struct FastOutput {
    static constexpr size_t BUFSZ = 1 << 20;
    char buf[BUFSZ];
    size_t pos = 0;

    ~FastOutput() { flush(); }

    inline void flush() {
        if (pos) {
            fwrite(buf, 1, pos, stdout);
            pos = 0;
        }
    }

    inline void writeChar(char c) {
        if (pos >= BUFSZ) flush();
        buf[pos++] = c;
    }

    inline void writeInt(int x) {
        if (x == 0) {
            writeChar('0');
            return;
        }
        if (x < 0) {
            writeChar('-');
            x = -x;
        }
        char s[24];
        int n = 0;
        while (x) {
            s[n++] = char('0' + (x % 10));
            x /= 10;
        }
        while (n--) writeChar(s[n]);
    }

    inline void writeNewline() { writeChar('\n'); }
};

struct Op { int x, y; };

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int n, m;
    if (!fs.readInt(n)) return 0;
    fs.readInt(m);

    int E = n + 1;

    vector<vector<int>> st(n + 2);
    st.assign(n + 2, {});
    for (int i = 1; i <= n; i++) {
        st[i].reserve(m);
        for (int j = 0; j < m; j++) {
            int c; fs.readInt(c);
            st[i].push_back(c);
        }
    }

    if (n == 1) {
        FastOutput fo;
        fo.writeInt(0);
        fo.writeNewline();
        return 0;
    }

    vector<vector<int>> cnt(n + 2, vector<int>(n + 2, 0));
    for (int i = 1; i <= n; i++) {
        for (int v : st[i]) {
            if (1 <= v && v <= n) cnt[i][v]++;
        }
    }

    vector<char> solvedPillar(n + 2, 0);

    auto chooseHelper = [&](int exclude) -> int {
        if (exclude != 1) return 1;
        return 2; // n>=2 here
    };

    vector<Op> ops;
    ops.reserve(1 << 20);

    auto doMove = [&](int x, int y) {
        int color = st[x].back();
        st[x].pop_back();
        st[y].push_back(color);
        if (1 <= color && color <= n) {
            cnt[x][color]--;
            cnt[y][color]++;
        }
        ops.push_back({x, y});
    };

    auto liftToTop = [&](int p, int k) {
        if (k <= 0) return;
        int helper = chooseHelper(p);
        // helper -> E
        doMove(helper, E);
        // move k balls from p -> E
        for (int i = 0; i < k; i++) doMove(p, E);
        // move target (now on top of p) -> helper
        doMove(p, helper);
        // move k balls back E -> p
        for (int i = 0; i < k; i++) doMove(E, p);
        // move target back helper -> p (now on top)
        doMove(helper, p);
        // restore helper top from E
        doMove(E, helper);
    };

    auto findFirstNotColorFromTop = [&](int p, int c) -> int {
        for (int k = 0; k < m; k++) {
            if (st[p][m - 1 - k] != c) return k;
        }
        return -1;
    };

    auto findFirstColorFromTop = [&](int p, int c) -> int {
        for (int k = 0; k < m; k++) {
            if (st[p][m - 1 - k] == c) return k;
        }
        return -1;
    };

    auto swapAny = [&](int src, int dst, int k) {
        // swap top of dst with element at depth k from top in src
        doMove(dst, E);               // dst top to E
        for (int i = 0; i < k; i++) doMove(src, E); // move k above-target balls
        doMove(src, dst);             // target ball to dst
        for (int i = 0; i < k; i++) doMove(E, src); // restore above-target balls
        doMove(E, src);               // original dst top to src
    };

    // Choose one color to skip solving explicitly (its pillar will be determined at the end)
    int skipColor = 1;
    int bestNeed = -1;
    for (int c = 1; c <= n; c++) {
        int need = m - cnt[c][c];
        if (need > bestNeed) {
            bestNeed = need;
            skipColor = c;
        }
    }

    vector<int> order;
    order.reserve(n - 1);
    for (int c = 1; c <= n; c++) if (c != skipColor) order.push_back(c);
    sort(order.begin(), order.end(), [&](int a, int b) {
        int na = m - cnt[a][a];
        int nb = m - cnt[b][b];
        return na > nb;
    });

    auto findDonor = [&](int color, int target) -> int {
        // Prefer donor with top == color
        for (int p = 1; p <= n; p++) {
            if (p == target || solvedPillar[p]) continue;
            if (cnt[p][color] > 0 && st[p].back() == color) return p;
        }
        for (int p = 1; p <= n; p++) {
            if (p == target || solvedPillar[p]) continue;
            if (cnt[p][color] > 0) return p;
        }
        return -1;
    };

    for (int c : order) {
        int t = c;
        while (cnt[t][c] < m) {
            int kw = findFirstNotColorFromTop(t, c);
            if (kw < 0) break; // should not happen
            if (kw > 0) liftToTop(t, kw);

            int donor = findDonor(c, t);
            if (donor < 0) break; // should not happen if input is valid
            int kc = findFirstColorFromTop(donor, c);
            if (kc < 0) break; // should not happen

            swapAny(donor, t, kc);

            if ((int)ops.size() > 10000000) break;
        }
        solvedPillar[t] = 1;
        if ((int)ops.size() > 10000000) break;
    }

    FastOutput fo;
    fo.writeInt((int)ops.size());
    fo.writeNewline();
    for (auto &op : ops) {
        fo.writeInt(op.x);
        fo.writeChar(' ');
        fo.writeInt(op.y);
        fo.writeNewline();
    }
    fo.flush();
    return 0;
}