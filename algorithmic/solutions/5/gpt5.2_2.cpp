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

static inline void appendInt(string &s, int x) {
    char buf[16];
    int n = 0;
    if (x == 0) {
        s.push_back('0');
        return;
    }
    while (x > 0) {
        buf[n++] = char('0' + (x % 10));
        x /= 10;
    }
    for (int i = n - 1; i >= 0; --i) s.push_back(buf[i]);
}

struct XorShift64 {
    uint64_t x = 88172645463325252ull;
    uint64_t next() {
        x ^= x << 7;
        x ^= x >> 9;
        return x;
    }
};

static vector<int> buildGreedyTwoEnded(
    int start,
    const vector<int> &outStart, const vector<int> &outTo,
    const vector<int> &inStart, const vector<int> &inTo,
    const vector<int> &deg,
    vector<int> &vis, int &mark
) {
    ++mark;
    vector<int> prefix;
    vector<int> suffix;
    suffix.reserve(1024);
    suffix.push_back(start);
    vis[start] = mark;

    bool blockBack = false, blockFront = false;

    while (true) {
        bool changed = false;

        if (!blockBack) {
            int u = suffix.back();
            int best = -1, bestSc = -1;
            for (int ei = outStart[u]; ei < outStart[u + 1]; ++ei) {
                int v = outTo[ei];
                if (vis[v] != mark) {
                    int sc = deg[v];
                    if (sc > bestSc) {
                        bestSc = sc;
                        best = v;
                    }
                }
            }
            if (best != -1) {
                vis[best] = mark;
                suffix.push_back(best);
                changed = true;
            } else {
                blockBack = true;
            }
        }

        if (!blockFront) {
            int u = prefix.empty() ? suffix[0] : prefix.back();
            int best = -1, bestSc = -1;
            for (int ei = inStart[u]; ei < inStart[u + 1]; ++ei) {
                int v = inTo[ei];
                if (vis[v] != mark) {
                    int sc = deg[v];
                    if (sc > bestSc) {
                        bestSc = sc;
                        best = v;
                    }
                }
            }
            if (best != -1) {
                vis[best] = mark;
                prefix.push_back(best);
                changed = true;
            } else {
                blockFront = true;
            }
        }

        if (!changed) break;
    }

    vector<int> res;
    res.reserve(prefix.size() + suffix.size());
    for (size_t i = prefix.size(); i-- > 0; ) res.push_back(prefix[i]);
    for (int v : suffix) res.push_back(v);
    return res;
}

int main() {
    FastScanner fs;

    int n, m;
    if (!fs.readInt(n)) return 0;
    fs.readInt(m);

    for (int i = 0; i < 10; i++) {
        int tmp;
        fs.readInt(tmp);
    }

    vector<int> U(m), V(m);
    vector<int> outdeg(n, 0), indeg(n, 0);

    for (int i = 0; i < m; i++) {
        int u, v;
        fs.readInt(u);
        fs.readInt(v);
        --u; --v;
        U[i] = u; V[i] = v;
        outdeg[u]++;
        indeg[v]++;
    }

    vector<int> outStart(n + 1, 0), inStart(n + 1, 0);
    for (int i = 0; i < n; i++) {
        outStart[i + 1] = outStart[i] + outdeg[i];
        inStart[i + 1] = inStart[i] + indeg[i];
    }

    vector<int> outTo(m), inTo(m);
    vector<int> outPos = outStart, inPos = inStart;
    for (int i = 0; i < m; i++) {
        int u = U[i], v = V[i];
        outTo[outPos[u]++] = v;
        inTo[inPos[v]++] = u;
    }
    U.clear(); V.clear();
    U.shrink_to_fit(); V.shrink_to_fit();

    vector<int> deg(n);
    for (int i = 0; i < n; i++) deg[i] = outdeg[i] + indeg[i];

    // Try DAG longest path via Kahn.
    vector<int> indegCopy = indeg;
    vector<int> q;
    q.reserve(n);
    for (int i = 0; i < n; i++) if (indegCopy[i] == 0) q.push_back(i);
    vector<int> topo;
    topo.reserve(n);
    for (size_t head = 0; head < q.size(); ++head) {
        int u = q[head];
        topo.push_back(u);
        for (int ei = outStart[u]; ei < outStart[u + 1]; ++ei) {
            int v = outTo[ei];
            if (--indegCopy[v] == 0) q.push_back(v);
        }
    }

    vector<int> bestPath;

    if ((int)topo.size() == n) {
        vector<int> dp(n, 1), parent(n, -1);
        int bestEnd = 0;
        for (int u : topo) {
            if (dp[u] > dp[bestEnd]) bestEnd = u;
            int du = dp[u];
            for (int ei = outStart[u]; ei < outStart[u + 1]; ++ei) {
                int v = outTo[ei];
                if (dp[v] < du + 1) {
                    dp[v] = du + 1;
                    parent[v] = u;
                }
            }
        }
        for (int i = 0; i < n; i++) if (dp[i] > dp[bestEnd]) bestEnd = i;

        vector<int> path;
        for (int cur = bestEnd; cur != -1; cur = parent[cur]) path.push_back(cur);
        reverse(path.begin(), path.end());
        bestPath = std::move(path);
    } else {
        // Greedy multi-start.
        vector<int> starts;
        starts.reserve(64);
        starts.push_back(0);

        const int K = 25;
        priority_queue<pair<int,int>, vector<pair<int,int>>, greater<pair<int,int>>> pq;
        for (int i = 0; i < n; i++) {
            int d = deg[i];
            if ((int)pq.size() < K) pq.push({d, i});
            else if (d > pq.top().first) { pq.pop(); pq.push({d, i}); }
        }
        while (!pq.empty()) {
            starts.push_back(pq.top().second);
            pq.pop();
        }

        XorShift64 rng;
        const int R = 20;
        for (int i = 0; i < R; i++) starts.push_back((int)(rng.next() % (uint64_t)n));

        sort(starts.begin(), starts.end());
        starts.erase(unique(starts.begin(), starts.end()), starts.end());
        if ((int)starts.size() > 30) starts.resize(30);

        vector<int> vis(n, 0);
        int mark = 0;

        bestPath = buildGreedyTwoEnded(starts[0], outStart, outTo, inStart, inTo, deg, vis, mark);
        if ((int)bestPath.size() < n) {
            for (size_t i = 1; i < starts.size(); i++) {
                auto path = buildGreedyTwoEnded(starts[i], outStart, outTo, inStart, inTo, deg, vis, mark);
                if (path.size() > bestPath.size()) bestPath = std::move(path);
                if ((int)bestPath.size() == n) break;
            }
        }
    }

    if (bestPath.empty()) bestPath.push_back(0);

    string out;
    out.reserve(32 + bestPath.size() * 7);

    appendInt(out, (int)bestPath.size());
    out.push_back('\n');
    for (size_t i = 0; i < bestPath.size(); i++) {
        if (i) out.push_back(' ');
        appendInt(out, bestPath[i] + 1);
    }
    out.push_back('\n');

    fwrite(out.data(), 1, out.size(), stdout);
    return 0;
}