#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static inline int gc() {
        static const int BUFSIZE = 1 << 20;
        static char buf[BUFSIZE];
        static int idx = 0, size = 0;
        if (idx >= size) {
            size = fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return EOF;
        }
        return buf[idx++];
    }
    template<typename T>
    bool readInt(T &out) {
        int c, neg = 0;
        T val = 0;
        c = gc();
        if (c == EOF) return false;
        while (c != EOF && c <= ' ') c = gc();
        if (c == EOF) return false;
        if (c == '-') { neg = 1; c = gc(); }
        for (; c >= '0' && c <= '9'; c = gc()) val = val * 10 + (c - '0');
        out = neg ? -val : val;
        return true;
    }
    bool readDouble(double &out) {
        int c = gc();
        if (c == EOF) return false;
        while (c != EOF && c <= ' ') c = gc();
        if (c == EOF) return false;
        int neg = 0;
        if (c == '-') { neg = 1; c = gc(); }
        long long intPart = 0;
        while (c >= '0' && c <= '9') {
            intPart = intPart * 10 + (c - '0');
            c = gc();
        }
        double frac = 0.0, base = 1.0;
        if (c == '.') {
            c = gc();
            while (c >= '0' && c <= '9') {
                frac = frac * 10.0 + (c - '0');
                base *= 10.0;
                c = gc();
            }
        }
        out = (double)intPart + frac / base;
        if (neg) out = -out;
        // skip rest token if any (like exponent), but not expected here
        return true;
    }
} In;

struct FastOutput {
    static const int BUFSIZE = 1 << 20;
    char buf[BUFSIZE];
    int idx = 0;
    ~FastOutput() { flush(); }
    inline void flush() {
        if (idx) {
            fwrite(buf, 1, idx, stdout);
            idx = 0;
        }
    }
    inline void pc(char c) {
        if (idx >= BUFSIZE) flush();
        buf[idx++] = c;
    }
    inline void writeInt(int x, char endc) {
        if (x == 0) {
            pc('0');
            pc(endc);
            return;
        }
        if (x < 0) {
            pc('-');
            x = -x;
        }
        char s[20];
        int n = 0;
        while (x) {
            s[n++] = char('0' + (x % 10));
            x /= 10;
        }
        while (n--) pc(s[n]);
        pc(endc);
    }
} Out;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, k;
    long long m_input;
    double eps;
    if (!In.readInt(n)) return 0;
    In.readInt(m_input);
    In.readInt(k);
    In.readDouble(eps);

    vector<int> deg(n + 1, 0);
    vector<int> U;
    vector<int> V;
    U.reserve((size_t)m_input);
    V.reserve((size_t)m_input);

    for (long long i = 0; i < m_input; ++i) {
        int u, v;
        if (!In.readInt(u)) u = 0;
        In.readInt(v);
        if (u < 1 || u > n || v < 1 || v > n) continue;
        if (u == v) continue; // ignore self-loops
        U.push_back(u);
        V.push_back(v);
        deg[u]++;
        deg[v]++;
    }

    // Build CSR adjacency
    vector<int> off(n + 2, 0);
    for (int i = 1; i <= n; ++i) off[i + 1] = off[i] + deg[i];
    vector<int> adj;
    adj.resize(off[n + 1]);
    vector<int> cur = off;
    const size_t m2 = U.size();
    for (size_t i = 0; i < m2; ++i) {
        int u = U[i], v = V[i];
        adj[cur[u]++] = v;
        adj[cur[v]++] = u;
    }
    U.clear(); V.clear(); U.shrink_to_fit(); V.shrink_to_fit();

    // capacity
    long long ideal = (n + (long long)k - 1) / (long long)k;
    long double capLD = floor(((long double)1.0 + (long double)eps) * (long double)ideal + 1e-12L);
    int cap = (int)capLD;
    if (cap < 1) cap = 1;

    // Choose seeds: top-k degrees
    struct NodeDeg { int deg, id; };
    struct CmpMin { bool operator()(const NodeDeg &a, const NodeDeg &b) const {
        if (a.deg != b.deg) return a.deg > b.deg; // reversed for min-heap behavior via priority_queue default
        return a.id > b.id;
    }};
    priority_queue<NodeDeg, vector<NodeDeg>, CmpMin> pq; // min-heap by (deg,id)
    for (int i = 1; i <= n; ++i) {
        if ((int)pq.size() < k) {
            pq.push({deg[i], i});
        } else if (deg[i] > pq.top().deg) {
            pq.pop();
            pq.push({deg[i], i});
        }
    }
    vector<int> seeds;
    seeds.reserve(k);
    while (!pq.empty()) {
        seeds.push_back(pq.top().id);
        pq.pop();
    }
    // sort seeds by degree descending
    sort(seeds.begin(), seeds.end(), [&](int a, int b){
        if (deg[a] != deg[b]) return deg[a] > deg[b];
        return a < b;
    });

    // BFS order from seeds
    vector<char> vis(n + 1, 0);
    vector<int> order;
    order.reserve(n);
    deque<int> q;
    for (int s : seeds) {
        if (s < 1 || s > n) continue;
        if (vis[s]) continue;
        vis[s] = 1;
        q.push_back(s);
        while (!q.empty()) {
            int u = q.front(); q.pop_front();
            order.push_back(u);
            for (int ei = off[u]; ei < off[u + 1]; ++ei) {
                int w = adj[ei];
                if (!vis[w]) {
                    vis[w] = 1;
                    q.push_back(w);
                }
            }
        }
    }
    for (int i = 1; i <= n; ++i) {
        if (!vis[i]) {
            vis[i] = 1;
            q.push_back(i);
            while (!q.empty()) {
                int u = q.front(); q.pop_front();
                order.push_back(u);
                for (int ei = off[u]; ei < off[u + 1]; ++ei) {
                    int w = adj[ei];
                    if (!vis[w]) {
                        vis[w] = 1;
                        q.push_back(w);
                    }
                }
            }
        }
    }

    // Partition assignment using LDG-like heuristic
    vector<int> part(n + 1, 0);
    vector<int> load(k + 1, 0);
    vector<long long> comm(k + 1, 0);

    // For counting neighbors' parts efficiently
    vector<int> seen(k + 1, 0), cnt(k + 1, 0);
    int iterMark = 1;

    // Min-heap for minimal load part among non-full
    struct HeapNode { int load, p; };
    struct CmpHeap {
        bool operator()(const HeapNode &a, const HeapNode &b) const {
            if (a.load != b.load) return a.load > b.load;
            return a.p > b.p;
        }
    };
    priority_queue<HeapNode, vector<HeapNode>, CmpHeap> heap;
    for (int j = 1; j <= k; ++j) heap.push({0, j});

    auto getMinLoadNonFull = [&]() -> int {
        while (!heap.empty()) {
            HeapNode top = heap.top();
            if (top.load != load[top.p] || load[top.p] >= cap) {
                heap.pop();
                continue;
            }
            return top.p;
        }
        // all full unlikely; fallback to min load even if full (should not happen)
        int best = 1;
        for (int j = 2; j <= k; ++j) if (load[j] < load[best]) best = j;
        return best;
    };

    const double balanceStrength = 0.7; // modest balance penalty

    vector<int> touched; touched.reserve(64);

    for (int idx = 0; idx < n; ++idx) {
        int v = order[idx];
        // build neighbor part counts
        ++iterMark;
        if (iterMark == INT_MAX/2) {
            iterMark = 1;
            fill(seen.begin(), seen.end(), 0);
        }
        touched.clear();
        for (int ei = off[v]; ei < off[v + 1]; ++ei) {
            int u = adj[ei];
            int p = part[u];
            if (p > 0) {
                if (seen[p] != iterMark) {
                    seen[p] = iterMark;
                    cnt[p] = 1;
                    touched.push_back(p);
                } else {
                    cnt[p]++;
                }
            }
        }
        int fallback = getMinLoadNonFull();
        int bestP = -1;
        double bestScore = -1e100;
        // consider touched parts
        for (int p : touched) {
            if (load[p] >= cap) continue;
            double score = (double)cnt[p] - balanceStrength * (double)load[p] / (double)cap;
            if (score > bestScore || (score == bestScore && load[p] < load[bestP]) || (score == bestScore && load[p] == load[bestP] && p < bestP)) {
                bestScore = score;
                bestP = p;
            }
        }
        if (bestP == -1) {
            // consider fallback
            int p = fallback;
            if (load[p] < cap) {
                double seenCnt = (seen[p] == iterMark ? (double)cnt[p] : 0.0);
                double score = seenCnt - balanceStrength * (double)load[p] / (double)cap;
                bestP = p;
                bestScore = score;
            } else {
                // extremely unlikely; scan for any available
                int best = -1;
                int minLoad = INT_MAX;
                for (int j = 1; j <= k; ++j) {
                    if (load[j] < minLoad && load[j] < cap) {
                        minLoad = load[j];
                        best = j;
                    }
                }
                if (best == -1) {
                    // all full, choose absolute minimal load (violates balance, should not happen)
                    best = 1;
                    for (int j = 2; j <= k; ++j) if (load[j] < load[best]) best = j;
                }
                bestP = best;
            }
        }
        // compute approximate F for v
        int distinctParts = (int)touched.size();
        int Fv = distinctParts - ((seen[bestP] == iterMark) ? 1 : 0);
        comm[bestP] += Fv;

        part[v] = bestP;
        load[bestP]++;
        heap.push({load[bestP], bestP});
    }

    // One local refinement pass (optional)
    {
        int moves = 0;
        for (int idx = 0; idx < n; ++idx) {
            int v = order[idx];
            int Pv = part[v];
            ++iterMark;
            if (iterMark == INT_MAX/2) {
                iterMark = 1;
                fill(seen.begin(), seen.end(), 0);
            }
            touched.clear();
            for (int ei = off[v]; ei < off[v + 1]; ++ei) {
                int u = adj[ei];
                int p = part[u];
                if (p > 0) {
                    if (seen[p] != iterMark) {
                        seen[p] = iterMark;
                        cnt[p] = 1;
                        touched.push_back(p);
                    } else {
                        cnt[p]++;
                    }
                }
            }
            int currCount = (seen[Pv] == iterMark) ? cnt[Pv] : 0;
            int bestP = Pv;
            int bestCount = currCount;
            int bestLoad = load[Pv];
            for (int p : touched) {
                if (p == Pv) continue;
                if (load[p] >= cap) continue;
                int c = cnt[p];
                if (c > bestCount || (c == bestCount && load[p] < bestLoad)) {
                    bestCount = c;
                    bestP = p;
                    bestLoad = load[p];
                }
            }
            if (bestP != Pv) {
                int delta = bestCount - currCount;
                int distinctParts = (int)touched.size();
                int F_old = distinctParts - ((seen[Pv] == iterMark) ? 1 : 0);
                int F_new = distinctParts - ((seen[bestP] == iterMark) ? 1 : 0);
                if (delta > 0 || (delta == 0 && F_new < F_old)) {
                    // move if capacity allows
                    if (load[bestP] + 1 <= cap) {
                        part[v] = bestP;
                        load[Pv]--; load[bestP]++;
                        comm[Pv] -= F_old; comm[bestP] += F_new;
                        heap.push({load[Pv], Pv});
                        heap.push({load[bestP], bestP});
                        moves++;
                    }
                }
            }
        }
        (void)moves;
    }

    // Output
    for (int i = 1; i <= n; ++i) {
        Out.writeInt(part[i] >= 1 ? part[i] : 1, (i == n) ? '\n' : ' ');
    }
    Out.flush();
    return 0;
}