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

struct FastOutput {
    static constexpr size_t BUFSIZE = 1 << 20;
    size_t idx = 0;
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

    inline void writeInt(int x) {
        if (x == 0) {
            pushChar('0');
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
    }
};

struct Op { int x, y; };

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int n, m;
    if (!fs.readInt(n)) return 0;
    fs.readInt(m);

    int P = n + 1;
    int bufP = n + 1;
    int stride = n + 1;

    vector<vector<int>> st(P + 1);
    vector<char> fixedP(P + 1, 0);

    // counts stored as cnt[p * stride + color], colors are 1..n
    vector<int> cnt((P + 1) * stride, 0);
    auto C = [&](int p, int color) -> int& {
        return cnt[p * stride + color];
    };

    for (int i = 1; i <= n; i++) {
        st[i].reserve(m);
        for (int j = 0; j < m; j++) {
            int col; fs.readInt(col);
            st[i].push_back(col);
            if (1 <= col && col <= n) C(i, col)++;
        }
    }
    // buffer pillar empty

    vector<int> spaceList;
    vector<int> pos(P + 1, -1);
    int ptr = 0;

    auto updateSpace = [&](int i) {
        bool should = (!fixedP[i] && (int)st[i].size() < m);
        int &pi = pos[i];
        if (should) {
            if (pi == -1) {
                pi = (int)spaceList.size();
                spaceList.push_back(i);
            }
        } else {
            if (pi != -1) {
                int last = spaceList.back();
                spaceList[pi] = last;
                pos[last] = pi;
                spaceList.pop_back();
                pi = -1;
                if (ptr > (int)spaceList.size()) ptr = 0;
            }
        }
    };

    for (int i = 1; i <= P; i++) updateSpace(i);

    vector<Op> ops;
    ops.reserve(200000);

    auto doMove = [&](int x, int y) {
        int col = st[x].back();
        st[x].pop_back();
        st[y].push_back(col);
        if (1 <= col && col <= n) {
            C(x, col)--;
            C(y, col)++;
        }
        ops.push_back({x, y});
        updateSpace(x);
        updateSpace(y);
    };

    auto chooseDest = [&](int source, int avoid) -> int {
        if (bufP != source && bufP != avoid && pos[bufP] != -1) return bufP;
        int sz = (int)spaceList.size();
        if (sz == 0) return -1;
        if (ptr >= sz) ptr = 0;
        for (int tries = 0; tries < sz; tries++) {
            int i = spaceList[ptr];
            ptr++;
            if (ptr >= sz) ptr = 0;
            if (i != source && i != avoid) return i;
        }
        return -1;
    };

    auto chooseDestNoAvoid = [&](int source) -> int {
        if (bufP != source && pos[bufP] != -1) return bufP;
        int sz = (int)spaceList.size();
        if (sz == 0) return -1;
        if (ptr >= sz) ptr = 0;
        for (int tries = 0; tries < sz; tries++) {
            int i = spaceList[ptr];
            ptr++;
            if (ptr >= sz) ptr = 0;
            if (i != source) return i;
        }
        return -1;
    };

    auto findSource = [&](int color, int target) -> int {
        // Prefer a pillar whose top is color
        for (int i = 1; i <= P; i++) {
            if (i == target || fixedP[i] || st[i].empty()) continue;
            if (st[i].back() == color) return i;
        }
        // Fallback: any pillar with that color
        for (int i = 1; i <= P; i++) {
            if (i == target || fixedP[i]) continue;
            if (C(i, color) > 0) return i;
        }
        return -1;
    };

    for (int color = 1; color <= n; color++) {
        int target = color;
        while (C(target, color) < m) {
            if (!st[target].empty() && st[target].back() != color) {
                int dest = chooseDestNoAvoid(target);
                if (dest == -1) return 0;
                doMove(target, dest);
                continue;
            }
            if ((int)st[target].size() == m && C(target, color) < m) {
                int dest = chooseDestNoAvoid(target);
                if (dest == -1) return 0;
                doMove(target, dest);
                continue;
            }

            int p = findSource(color, target);
            if (p == -1) return 0;

            while (st[p].back() != color) {
                int dest = chooseDest(p, target);
                if (dest == -1) dest = chooseDestNoAvoid(p);
                if (dest == -1) return 0;
                doMove(p, dest);
            }
            // Move the color ball to target
            if ((int)st[target].size() == m) {
                // Ensure space (should rarely happen due to earlier checks)
                int dest = chooseDestNoAvoid(target);
                if (dest == -1) return 0;
                doMove(target, dest);
            }
            doMove(p, target);
        }
        fixedP[target] = 1;
        updateSpace(target);
    }

    // Output
    FastOutput fo;
    fo.writeInt((int)ops.size());
    fo.pushChar('\n');
    for (auto &op : ops) {
        fo.writeInt(op.x);
        fo.pushChar(' ');
        fo.writeInt(op.y);
        fo.pushChar('\n');
    }
    fo.flush();
    return 0;
}