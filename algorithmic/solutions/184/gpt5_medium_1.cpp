#include <bits/stdc++.h>
using namespace std;

static const int MAXN = 1005;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner() : idx(0), size(0) {}
    inline char getChar() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    bool readInt(int &out) {
        char c;
        int sgn = 1;
        int val = 0;
        c = getChar();
        if (!c) return false;
        while (c != '-' && (c < '0' || c > '9')) {
            c = getChar();
            if (!c) return false;
        }
        if (c == '-') {
            sgn = -1;
            c = getChar();
        }
        for (; c >= '0' && c <= '9'; c = getChar()) {
            val = val * 10 + (c - '0');
        }
        out = val * sgn;
        return true;
    }
} In;

struct RNG {
    uint64_t s;
    RNG() {
        uint64_t x = chrono::steady_clock::now().time_since_epoch().count();
        s = x ^ (x << 13) ^ (x >> 7);
        if (s == 0) s = 88172645463393265ull;
    }
    inline uint32_t next() {
        s ^= s << 7;
        s ^= s >> 9;
        s ^= s << 8;
        return (uint32_t)s;
    }
    inline int randint(int l, int r) { // inclusive
        return l + (int)(next() % (uint32_t)(r - l + 1));
    }
    template <class T>
    void shuffle_vec(vector<T> &a) {
        for (int i = (int)a.size() - 1; i > 0; --i) {
            int j = (int)(next() % (uint32_t)(i + 1));
            swap(a[i], a[j]);
        }
    }
} rng;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M;
    if (!In.readInt(N)) return 0;
    In.readInt(M);

    static bitset<MAXN> adjBits[MAXN];
    for (int i = 0; i < N; ++i) adjBits[i].reset();

    for (int i = 0; i < M; ++i) {
        int u, v;
        In.readInt(u); In.readInt(v);
        if (u == v) continue;
        --u; --v;
        if (u < 0 || u >= N || v < 0 || v >= N) continue;
        adjBits[u].set(v);
        adjBits[v].set(u);
    }

    vector<vector<int>> neigh(N);
    for (int i = 0; i < N; ++i) {
        neigh[i].reserve((int)adjBits[i].count());
        for (int j = 0; j < N; ++j) if (adjBits[i].test(j)) neigh[i].push_back(j);
        if (!neigh[i].empty()) rng.shuffle_vec(neigh[i]);
    }
    vector<int> deg0(N);
    for (int i = 0; i < N; ++i) deg0[i] = (int)neigh[i].size();

    auto startTime = chrono::steady_clock::now();
    auto timeLimit = startTime + chrono::milliseconds(1900);

    vector<char> bestS(N, 0);
    int bestK = 0;

    auto greedy_run = [&](vector<char> &inS) {
        vector<int> deg = deg0;
        vector<char> alive(N, 1);
        int aliveCount = N;
        vector<vector<int>> buckets(N);
        int minDeg = N;
        vector<int> order(N);
        for (int i = 0; i < N; ++i) order[i] = i;
        rng.shuffle_vec(order);
        for (int idx = 0; idx < N; ++idx) {
            int i = order[idx];
            buckets[deg[i]].push_back(i);
            if (deg[i] < minDeg) minDeg = deg[i];
        }
        auto push_bucket = [&](int node) {
            int d = deg[node];
            buckets[d].push_back(node);
            if (d < minDeg) minDeg = d;
        };
        auto removeVertex = [&](int r) {
            if (!alive[r]) return;
            alive[r] = 0;
            --aliveCount;
            for (int z : neigh[r]) if (alive[z]) {
                --deg[z];
                push_bucket(z);
            }
        };
        auto pick_from_bucket = [&](int d) -> int {
            auto &b = buckets[d];
            while (!b.empty()) {
                int idx = (int)(rng.next() % (uint32_t)b.size());
                int id = b[idx];
                b[idx] = b.back(); b.pop_back();
                if (alive[id] && deg[id] == d) return id;
            }
            return -1;
        };

        inS.assign(N, 0);
        while (aliveCount > 0) {
            while (minDeg < N) {
                int v = pick_from_bucket(minDeg);
                if (v != -1) {
                    inS[v] = 1;
                    removeVertex(v);
                    for (int u : neigh[v]) if (alive[u]) removeVertex(u);
                    break;
                } else {
                    int nd = minDeg + 1;
                    while (nd < N && buckets[nd].empty()) ++nd;
                    minDeg = nd;
                }
            }
            if (minDeg >= N) break;
        }
    };

    auto local_improve = [&](vector<char> &inS, long long timeBudgetMillis) {
        auto lsStart = chrono::steady_clock::now();
        auto lsEnd   = lsStart + chrono::milliseconds(timeBudgetMillis);
        vector<int> cnt(N, 0);
        int curK = 0;
        for (int v = 0; v < N; ++v) if (inS[v]) {
            ++curK;
            for (int w : neigh[v]) ++cnt[w];
        }
        // Ensure maximal (should already be, but just in case)
        deque<int> q;
        for (int i = 0; i < N; ++i) if (!inS[i] && cnt[i] == 0) q.push_back(i);
        while (!q.empty()) {
            int u = q.back(); q.pop_back();
            if (inS[u] || cnt[u] != 0) continue;
            inS[u] = 1; ++curK;
            for (int w : neigh[u]) ++cnt[w];
        }

        // Try improving by 1-swap + zero-additions
        vector<int> idxs(N);
        for (int i = 0; i < N; ++i) idxs[i] = i;

        while (chrono::steady_clock::now() < lsEnd) {
            rng.shuffle_vec(idxs);
            bool anyImproved = false;
            for (int i = 0; i < N && chrono::steady_clock::now() < lsEnd; ++i) {
                int u = idxs[i];
                if (inS[u] || cnt[u] != 1) continue;
                int s = -1;
                for (int w : neigh[u]) {
                    if (inS[w]) { s = w; break; }
                }
                if (s == -1) continue; // safety

                // Perform tentative swap
                // Remove s
                inS[s] = 0; --curK;
                for (int w : neigh[s]) --cnt[w];
                // Add u
                inS[u] = 1; ++curK;
                for (int w : neigh[u]) ++cnt[w];

                // Zero candidates among neighbors of s
                deque<int> zq;
                for (int w : neigh[s]) if (!inS[w] && cnt[w] == 0) zq.push_back(w);

                vector<int> added;
                while (!zq.empty()) {
                    int v = zq.back(); zq.pop_back();
                    if (inS[v] || cnt[v] != 0) continue;
                    inS[v] = 1; ++curK;
                    added.push_back(v);
                    for (int w : neigh[v]) ++cnt[w];
                }

                if ((int)added.size() >= 1) {
                    anyImproved = true;
                } else {
                    // No net improvement (delta = 0). Revert changes.
                    // Remove added zeros (none if size==0, but keep generic)
                    for (int k = (int)added.size() - 1; k >= 0; --k) {
                        int v = added[k];
                        inS[v] = 0; --curK;
                        for (int w : neigh[v]) --cnt[w];
                    }
                    // Remove u
                    inS[u] = 0; --curK;
                    for (int w : neigh[u]) --cnt[w];
                    // Add back s
                    inS[s] = 1; ++curK;
                    for (int w : neigh[s]) ++cnt[w];
                }
            }
            if (!anyImproved) break;
        }
        return;
    };

    // Main loop: multiple greedy runs with randomization and local improvements
    int runs = 0;
    while (chrono::steady_clock::now() < timeLimit) {
        vector<char> curS(N, 0);
        greedy_run(curS);
        int curK = 0;
        for (int i = 0; i < N; ++i) if (curS[i]) ++curK;

        auto now = chrono::steady_clock::now();
        if (now >= timeLimit) {
            if (curK > bestK) { bestK = curK; bestS = curS; }
            break;
        }

        // Allow some local search if time permits
        long long remaining = chrono::duration_cast<chrono::milliseconds>(timeLimit - now).count();
        if (remaining > 50) {
            long long budget = min<long long>(remaining - 20, 100); // up to 100ms per run if time available
            local_improve(curS, budget);
            curK = 0;
            for (int i = 0; i < N; ++i) if (curS[i]) ++curK;
        }

        if (curK > bestK) {
            bestK = curK;
            bestS = curS;
        }
        ++runs;
        if (chrono::steady_clock::now() >= timeLimit) break;
    }

    // Output best solution
    for (int i = 0; i < N; ++i) {
        char c = bestS[i] ? '1' : '0';
        putchar(c);
        putchar('\n');
    }
    return 0;
}