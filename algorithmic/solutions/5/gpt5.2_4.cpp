#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr int BUFSIZE = 1 << 20;
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

    inline void writeChar(char c) {
        if (idx >= BUFSIZE) flush();
        buf[idx++] = c;
    }

    inline void writeInt(long long x, char endc = 0) {
        if (x == 0) {
            writeChar('0');
            if (endc) writeChar(endc);
            return;
        }
        if (x < 0) {
            writeChar('-');
            x = -x;
        }
        char s[32];
        int n = 0;
        while (x) {
            s[n++] = char('0' + (x % 10));
            x /= 10;
        }
        for (int i = n - 1; i >= 0; --i) writeChar(s[i]);
        if (endc) writeChar(endc);
    }
};

static inline uint64_t splitmix64(uint64_t &x) {
    uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
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
    vector<int> outdeg(n + 1, 0), indegOrig(n + 1, 0);

    for (int i = 0; i < m; i++) {
        int u, v;
        fs.readInt(u);
        fs.readInt(v);
        U[i] = u;
        V[i] = v;
        outdeg[u]++;
        indegOrig[v]++;
    }

    vector<int> outStart(n + 2, 0), inStart(n + 2, 0);
    for (int i = 1; i <= n; i++) {
        outStart[i + 1] = outStart[i] + outdeg[i];
        inStart[i + 1] = inStart[i] + indegOrig[i];
    }

    vector<int> outTo(m), inTo(m);
    vector<int> outPos = outStart, inPos = inStart;
    for (int i = 0; i < m; i++) {
        int u = U[i], v = V[i];
        outTo[outPos[u]++] = v;
        inTo[inPos[v]++] = u;
    }
    vector<int>().swap(U);
    vector<int>().swap(V);

    // Try DAG longest path via topological sort.
    vector<int> indeg = indegOrig;
    vector<int> q;
    q.reserve(n);
    for (int i = 1; i <= n; i++) if (indeg[i] == 0) q.push_back(i);

    vector<int> topo;
    topo.reserve(n);
    for (size_t qi = 0; qi < q.size(); qi++) {
        int u = q[qi];
        topo.push_back(u);
        for (int e = outStart[u]; e < outStart[u + 1]; e++) {
            int v = outTo[e];
            if (--indeg[v] == 0) q.push_back(v);
        }
    }

    vector<int> bestPath;

    if ((int)topo.size() == n) {
        vector<int> dp(n + 1, 1), par(n + 1, -1);
        int bestEnd = 1, bestLen = 1;
        for (int u : topo) {
            int du = dp[u];
            for (int e = outStart[u]; e < outStart[u + 1]; e++) {
                int v = outTo[e];
                if (du + 1 > dp[v]) {
                    dp[v] = du + 1;
                    par[v] = u;
                }
            }
            if (dp[u] > bestLen) {
                bestLen = dp[u];
                bestEnd = u;
            }
        }
        for (int i = 1; i <= n; i++) {
            if (dp[i] > bestLen) {
                bestLen = dp[i];
                bestEnd = i;
            }
        }
        vector<int> path;
        path.reserve(bestLen);
        int cur = bestEnd;
        while (cur != -1) {
            path.push_back(cur);
            cur = par[cur];
        }
        reverse(path.begin(), path.end());
        bestPath = std::move(path);
    } else {
        // Fallback heuristic: bidirectional greedy from several starts.
        int maxOutV = 1;
        for (int i = 2; i <= n; i++) if (outdeg[i] > outdeg[maxOutV]) maxOutV = i;

        int anyIndeg0 = -1;
        for (int i = 1; i <= n; i++) if (indegOrig[i] == 0) { anyIndeg0 = i; break; }

        vector<int> starts;
        starts.reserve(16);
        starts.push_back(1);
        starts.push_back(maxOutV);
        if (anyIndeg0 != -1) starts.push_back(anyIndeg0);

        uint64_t seed = 123456789123456789ULL ^ (uint64_t)n ^ ((uint64_t)m << 1);
        int targetAttempts = 10;
        while ((int)starts.size() < targetAttempts) {
            int v = (int)(splitmix64(seed) % (uint64_t)n) + 1;
            starts.push_back(v);
        }
        sort(starts.begin(), starts.end());
        starts.erase(unique(starts.begin(), starts.end()), starts.end());

        vector<int> vis(n + 1, 0);
        int stamp = 0;

        auto getBestOut = [&](int u, int st) -> int {
            int best = -1;
            int bestScore = -1;
            for (int e = outStart[u]; e < outStart[u + 1]; e++) {
                int v = outTo[e];
                if (vis[v] == st) continue;
                int score = outdeg[v];
                if (score > bestScore) {
                    bestScore = score;
                    best = v;
                }
            }
            return best;
        };
        auto getBestIn = [&](int u, int st) -> int {
            int best = -1;
            int bestScore = -1;
            for (int e = inStart[u]; e < inStart[u + 1]; e++) {
                int v = inTo[e]; // v -> u
                if (vis[v] == st) continue;
                int score = outdeg[v];
                if (score > bestScore) {
                    bestScore = score;
                    best = v;
                }
            }
            return best;
        };

        size_t attempts = min<size_t>(starts.size(), 12);
        for (size_t ai = 0; ai < attempts; ai++) {
            int s = starts[ai];
            stamp++;
            deque<int> dq;
            dq.push_back(s);
            vis[s] = stamp;

            while (true) {
                int back = dq.back();
                int nxt = getBestOut(back, stamp);
                if (nxt != -1) {
                    dq.push_back(nxt);
                    vis[nxt] = stamp;
                    continue;
                }
                int front = dq.front();
                int pre = getBestIn(front, stamp);
                if (pre != -1) {
                    dq.push_front(pre);
                    vis[pre] = stamp;
                    continue;
                }
                break;
            }

            if (dq.size() > bestPath.size()) {
                bestPath.assign(dq.begin(), dq.end());
                if (bestPath.size() == (size_t)n) break;
            }
        }

        if (bestPath.empty()) bestPath = {1};
    }

    FastOutput fo;
    fo.writeInt((int)bestPath.size(), '\n');
    for (size_t i = 0; i < bestPath.size(); i++) {
        fo.writeInt(bestPath[i], (i + 1 == bestPath.size()) ? '\n' : ' ');
    }
    return 0;
}