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

    int nextInt() {
        char c;
        do c = readChar(); while (c && c <= ' ');
        int sgn = 1;
        if (c == '-') { sgn = -1; c = readChar(); }
        int x = 0;
        while (c >= '0' && c <= '9') {
            x = x * 10 + (c - '0');
            c = readChar();
        }
        return x * sgn;
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

    inline void writeInt(long long x) {
        if (x == 0) { pushChar('0'); return; }
        if (x < 0) { pushChar('-'); x = -x; }
        char s[24];
        int n = 0;
        while (x) { s[n++] = char('0' + (x % 10)); x /= 10; }
        while (n--) pushChar(s[n]);
    }

    inline void writeSpace() { pushChar(' '); }
    inline void writeNewline() { pushChar('\n'); }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    FastOutput fo;

    int T = fs.nextInt();
    while (T--) {
        int n = fs.nextInt();
        vector<int> p(n + 1), pos(n + 1);
        for (int i = 1; i <= n; i++) {
            p[i] = fs.nextInt();
            pos[p[i]] = i;
        }

        vector<vector<pair<int,int>>> adj(n + 1);
        vector<int> deg(n + 1, 0);
        for (int i = 1; i <= n - 1; i++) {
            int u = fs.nextInt(), v = fs.nextInt();
            adj[u].push_back({v, i});
            adj[v].push_back({u, i});
            deg[u]++; deg[v]++;
        }

        vector<char> alive(n + 1, 1);
        deque<int> leaves;
        for (int i = 1; i <= n; i++) if (deg[i] <= 1) leaves.push_back(i);

        vector<int> parent(n + 1), parentEdge(n + 1), q(n + 1);
        vector<int> pathRev;
        vector<int> ops;
        ops.reserve(n * n / 2 + 5);

        auto applySwap = [&](int a, int b, int edgeIdx) {
            ops.push_back(edgeIdx);
            int ta = p[a], tb = p[b];
            p[a] = tb; p[b] = ta;
            pos[ta] = b;
            pos[tb] = a;
        };

        int aliveCount = n;
        while (aliveCount > 1) {
            int v = -1;
            while (!leaves.empty()) {
                int x = leaves.front(); leaves.pop_front();
                if (alive[x] && deg[x] <= 1) { v = x; break; }
            }
            if (v == -1) break; // should not happen

            if (p[v] != v) {
                int s = pos[v], t = v;
                if (s != t) {
                    fill(parent.begin(), parent.end(), -1);
                    int head = 0, tail = 0;
                    q[tail++] = s;
                    parent[s] = s;
                    parentEdge[s] = -1;

                    while (head < tail) {
                        int cur = q[head++];
                        if (cur == t) break;
                        for (auto [to, ei] : adj[cur]) {
                            if (!alive[to] || parent[to] != -1) continue;
                            parent[to] = cur;
                            parentEdge[to] = ei;
                            q[tail++] = to;
                        }
                    }

                    pathRev.clear();
                    int cur = t;
                    while (cur != s) {
                        pathRev.push_back(cur);
                        cur = parent[cur];
                    }
                    pathRev.push_back(s);

                    for (int i = (int)pathRev.size() - 1; i > 0; --i) {
                        int a = pathRev[i];
                        int b = pathRev[i - 1];
                        int ei = parentEdge[b];
                        applySwap(a, b, ei);
                    }
                }
            }

            // remove leaf v
            alive[v] = 0;
            aliveCount--;
            int u = -1;
            for (auto [to, ei] : adj[v]) {
                if (alive[to]) { u = to; break; }
            }
            if (u != -1) {
                deg[u]--;
                if (deg[u] == 1) leaves.push_back(u);
            }
            deg[v] = 0;
        }

        fo.writeInt((int)ops.size());
        fo.writeNewline();
        for (int ei : ops) {
            fo.writeInt(1);
            fo.writeSpace();
            fo.writeInt(ei);
            fo.writeNewline();
        }
    }

    return 0;
}