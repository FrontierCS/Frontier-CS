#include <bits/stdc++.h>
using namespace std;

// Fast input
struct FastScanner {
    static const int S = 1 << 20;
    int idx, size;
    char buf[S];
    FastScanner() : idx(0), size(0) {}
    inline char getChar() {
        if (idx >= size) {
            size = (int)fread(buf, 1, S, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    template <typename T>
    bool readInt(T &out) {
        char c; T sign = 1; T x = 0;
        c = getChar();
        if (!c) return false;
        while (c != '-' && (c < '0' || c > '9')) {
            c = getChar();
            if (!c) return false;
        }
        if (c == '-') { sign = -1; c = getChar(); }
        for (; c >= '0' && c <= '9'; c = getChar()) x = x * 10 + (c - '0');
        out = x * sign;
        return true;
    }
    bool readDouble(double &out) {
        char c = getChar();
        if (!c) return false;
        while (c != '-' && c != '.' && (c < '0' || c > '9')) {
            c = getChar();
            if (!c) return false;
        }
        string s;
        s.push_back(c);
        c = getChar();
        while (c == '-' || c == '.' || (c >= '0' && c <= '9') || c == 'e' || c == 'E' || c == '+') {
            s.push_back(c);
            c = getChar();
        }
        out = atof(s.c_str());
        return true;
    }
};

// Fast output
struct FastOutput {
    static const int S = 1 << 20;
    int idx;
    char buf[S];
    FastOutput() : idx(0) {}
    ~FastOutput() { flush(); }
    inline void pushChar(char c) {
        if (idx >= S) flush();
        buf[idx++] = c;
    }
    inline void writeInt(int x, char end) {
        if (x == 0) {
            pushChar('0'); pushChar(end); return;
        }
        if (x < 0) {
            pushChar('-');
            x = -x;
        }
        char s[20];
        int n = 0;
        while (x) {
            s[n++] = char('0' + (x % 10));
            x /= 10;
        }
        for (int i = n - 1; i >= 0; --i) pushChar(s[i]);
        pushChar(end);
    }
    inline void flush() {
        if (idx) {
            fwrite(buf, 1, idx, stdout);
            idx = 0;
        }
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int n, m, k;
    double eps;
    if (!fs.readInt(n)) return 0;
    fs.readInt(m);
    fs.readInt(k);
    fs.readDouble(eps);

    vector<vector<int>> g(n + 1);
    vector<int> deg(n + 1, 0);

    g.reserve(n + 1);
    for (int i = 0; i < m; ++i) {
        int u, v;
        fs.readInt(u);
        fs.readInt(v);
        if (u < 1 || u > n || v < 1 || v > n) continue;
        if (u == v) continue; // ignore self-loops
        g[u].push_back(v);
        g[v].push_back(u);
        deg[u]++;
        deg[v]++;
    }

    long long ideal = (n + k - 1) / (long long)k; // ceil(n/k)
    long long cap_ll = (long long)floor((long double)ideal * ((long double)1.0 + (long double)eps));
    if (cap_ll < 1) cap_ll = 1;
    int cap = (int)cap_ll;

    // Seed selection: pick high-degree nodes, try to spread (not adjacent where possible)
    vector<int> order(n);
    iota(order.begin(), order.end(), 1);
    sort(order.begin(), order.end(), [&](int a, int b){ return deg[a] > deg[b]; });

    vector<int> seeds;
    seeds.reserve(min(k, n));
    vector<char> blocked(n + 1, 0), selected(n + 1, 0);

    for (int u : order) {
        if ((int)seeds.size() == k) break;
        if (blocked[u]) continue;
        seeds.push_back(u);
        selected[u] = 1;
        blocked[u] = 1;
        for (int v : g[u]) blocked[v] = 1;
    }
    if ((int)seeds.size() < k) {
        for (int u : order) {
            if ((int)seeds.size() == k) break;
            if (!selected[u]) {
                seeds.push_back(u);
                selected[u] = 1;
            }
        }
    }

    vector<int> part(n + 1, 0);
    vector<int> sz(k + 1, 0);

    vector<vector<int>> queues(k + 1);
    vector<size_t> head(k + 1, 0);
    for (int t = 1; t <= k; ++t) queues[t].reserve(16); // small initial

    int assigned = 0;
    int seedParts = min((int)seeds.size(), k);
    for (int i = 0; i < seedParts; ++i) {
        int s = seeds[i];
        int t = i + 1;
        if (part[s] == 0) {
            part[s] = t;
            sz[t]++;
            assigned++;
            for (int v : g[s]) if (part[v] == 0) queues[t].push_back(v);
        }
    }

    int nextId = 1;
    while (assigned < n) {
        int prevAssigned = assigned;
        for (int t = 1; t <= k; ++t) {
            if (sz[t] >= cap) continue;
            auto &q = queues[t];
            auto &h = head[t];
            while (sz[t] < cap && h < q.size()) {
                int u = q[h++];
                if (part[u] != 0) continue;
                part[u] = t;
                sz[t]++;
                assigned++;
                for (int v : g[u]) if (part[v] == 0) q.push_back(v);
            }
            if (assigned >= n) break;
        }
        if (assigned == prevAssigned) {
            int bestT = -1, bestSize = INT_MAX;
            for (int t = 1; t <= k; ++t) {
                if (sz[t] < cap && sz[t] < bestSize) {
                    bestSize = sz[t];
                    bestT = t;
                }
            }
            if (bestT == -1) break; // shouldn't happen
            while (nextId <= n && part[nextId] != 0) ++nextId;
            if (nextId > n) break; // safety
            int v = nextId;
            part[v] = bestT;
            sz[bestT]++;
            assigned++;
            for (int w : g[v]) if (part[w] == 0) queues[bestT].push_back(w);
        }
    }

    // Final fallback (if any still unassigned, assign to smallest available part)
    if (assigned < n) {
        for (int u = 1; u <= n; ++u) {
            if (part[u] == 0) {
                int bestT = -1, bestSize = INT_MAX;
                for (int t = 1; t <= k; ++t) {
                    if (sz[t] < cap && sz[t] < bestSize) {
                        bestSize = sz[t];
                        bestT = t;
                    }
                }
                if (bestT == -1) bestT = 1;
                part[u] = bestT;
                sz[bestT]++;
                assigned++;
            }
        }
    }

    // Local refinement: simple greedy EC improvement with capacity constraint
    // Use two passes: forward and backward
    vector<int> seen(k + 1, 0), cnt(k + 1, 0);
    int stamp = 1;

    for (int pass = 0; pass < 2; ++pass) {
        bool movedAny = false;
        if (pass == 0) {
            for (int u = 1; u <= n; ++u) {
                if (g[u].empty()) continue;
                int a = part[u];
                int inA = 0;
                ++stamp;
                if (stamp == INT_MAX / 2) { // reset to avoid overflow
                    fill(seen.begin(), seen.end(), 0);
                    stamp = 1;
                }
                vector<int> touched;
                touched.reserve(8);
                for (int v : g[u]) {
                    int t = part[v];
                    if (t == a) { inA++; }
                    else {
                        if (seen[t] != stamp) {
                            seen[t] = stamp;
                            cnt[t] = 1;
                            touched.push_back(t);
                        } else {
                            cnt[t]++;
                        }
                    }
                }
                int bestT = -1, bestC = -1;
                for (int t : touched) {
                    if (sz[t] >= cap) continue;
                    int c = cnt[t];
                    if (c > bestC) {
                        bestC = c;
                        bestT = t;
                    }
                }
                if (bestT != -1 && bestC > inA) {
                    sz[a]--;
                    sz[bestT]++;
                    part[u] = bestT;
                    movedAny = true;
                }
            }
        } else {
            for (int u = n; u >= 1; --u) {
                if (g[u].empty()) continue;
                int a = part[u];
                int inA = 0;
                ++stamp;
                if (stamp == INT_MAX / 2) {
                    fill(seen.begin(), seen.end(), 0);
                    stamp = 1;
                }
                vector<int> touched;
                touched.reserve(8);
                for (int v : g[u]) {
                    int t = part[v];
                    if (t == a) { inA++; }
                    else {
                        if (seen[t] != stamp) {
                            seen[t] = stamp;
                            cnt[t] = 1;
                            touched.push_back(t);
                        } else {
                            cnt[t]++;
                        }
                    }
                }
                int bestT = -1, bestC = -1;
                for (int t : touched) {
                    if (sz[t] >= cap) continue;
                    int c = cnt[t];
                    if (c > bestC) {
                        bestC = c;
                        bestT = t;
                    }
                }
                if (bestT != -1 && bestC > inA) {
                    sz[a]--;
                    sz[bestT]++;
                    part[u] = bestT;
                    movedAny = true;
                }
            }
        }
        if (!movedAny) break;
    }

    // Output
    FastOutput fo;
    for (int i = 1; i <= n; ++i) {
        int label = part[i];
        if (label < 1 || label > k) label = 1;
        fo.writeInt(label, i == n ? '\n' : ' ');
    }
    fo.flush();
    return 0;
}