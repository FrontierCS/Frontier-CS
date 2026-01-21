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

    inline void writeStr(const char* s) {
        while (*s) pushChar(*s++);
    }

    inline void writeNewline() { pushChar('\n'); }
};

struct AdjEdge {
    int to, id;
};

int main() {
    FastScanner fs;
    FastOutput fo;

    int T;
    if (!fs.readInt(T)) return 0;

    while (T--) {
        int n;
        fs.readInt(n);

        vector<int> p(n + 1), pos(n + 1);
        for (int i = 1; i <= n; i++) {
            fs.readInt(p[i]);
            pos[p[i]] = i;
        }

        vector<vector<AdjEdge>> adj(n + 1);
        adj.assign(n + 1, {});
        for (int i = 1; i <= n - 1; i++) {
            int u, v;
            fs.readInt(u);
            fs.readInt(v);
            adj[u].push_back({v, i});
            adj[v].push_back({u, i});
        }

        vector<char> active(n + 1, 1);
        vector<int> deg(n + 1, 0);
        deque<int> dq;
        for (int i = 1; i <= n; i++) {
            deg[i] = (int)adj[i].size();
        }
        for (int i = 1; i <= n; i++) {
            if (deg[i] <= 1) dq.push_back(i);
        }

        vector<int> ops;
        ops.reserve(n * n);

        vector<char> vis(n + 1, 0);
        vector<int> parent(n + 1, 0), parentE(n + 1, 0);
        vector<int> st;
        st.reserve(n);

        auto doSwap = [&](int a, int b, int eid) {
            ops.push_back(eid);
            int pa = p[a], pb = p[b];
            p[a] = pb; p[b] = pa;
            pos[pa] = b;
            pos[pb] = a;
        };

        int activeCount = n;
        while (activeCount > 1) {
            int v = -1;
            while (!dq.empty()) {
                int x = dq.front();
                dq.pop_front();
                if (active[x] && deg[x] == 1) {
                    v = x;
                    break;
                }
            }
            if (v == -1) break; // should not happen

            int start = pos[v];
            if (start != v) {
                fill(vis.begin(), vis.end(), 0);
                st.clear();
                st.push_back(v);
                vis[v] = 1;
                parent[v] = 0;
                parentE[v] = 0;

                while (!st.empty()) {
                    int cur = st.back();
                    st.pop_back();
                    if (cur == start) break;
                    for (const auto &e : adj[cur]) {
                        int to = e.to;
                        if (!active[to] || vis[to]) continue;
                        vis[to] = 1;
                        parent[to] = cur;
                        parentE[to] = e.id;
                        st.push_back(to);
                    }
                }

                int cur = start;
                while (cur != v) {
                    int nxt = parent[cur];
                    int eid = parentE[cur];
                    doSwap(cur, nxt, eid);
                    cur = nxt;
                }
            }

            active[v] = 0;
            activeCount--;
            int neigh = 0;
            for (const auto &e : adj[v]) {
                if (active[e.to]) {
                    neigh = e.to;
                    break;
                }
            }
            if (neigh) {
                deg[neigh]--;
                if (deg[neigh] == 1 && activeCount > 1) dq.push_back(neigh);
            }
            deg[v] = 0;
        }

        fo.writeInt((long long)ops.size());
        fo.writeNewline();
        for (int eid : ops) {
            fo.writeInt(1);
            fo.pushChar(' ');
            fo.writeInt(eid);
            fo.writeNewline();
        }
    }

    fo.flush();
    return 0;
}