#include <bits/stdc++.h>
using namespace std;

static const int KDR[8] = {+2,+2,+1,+1,-1,-1,-2,-2};
static const int KDC[8] = {+1,-1,+2,-2,+2,-2,+1,-1};

struct XorShift64 {
    uint64_t x;
    explicit XorShift64(uint64_t seed=88172645463325252ull) : x(seed ? seed : 88172645463325252ull) {}
    inline uint64_t nextU64() {
        x ^= x << 7;
        x ^= x >> 9;
        return x;
    }
};

struct FastOutput {
    string buf;
    FastOutput() { buf.reserve(8 << 20); }
    inline void ensure(size_t add) {
        if (buf.size() + add > buf.capacity()) buf.reserve(max(buf.capacity() * 2, buf.size() + add));
    }
    inline void pushChar(char c) { buf.push_back(c); }
    inline void pushStr(const char* s) { buf.append(s); }
    inline void pushInt(int v) {
        char tmp[16];
        int n = 0;
        if (v == 0) {
            buf.push_back('0');
            return;
        }
        if (v < 0) { buf.push_back('-'); v = -v; }
        while (v > 0) {
            tmp[n++] = char('0' + (v % 10));
            v /= 10;
        }
        while (n--) buf.push_back(tmp[n]);
    }
    void flush() {
        fwrite(buf.data(), 1, buf.size(), stdout);
        buf.clear();
    }
};

struct Solver {
    int N;
    int sr, sc;
    int M;
    int startId;
    int target;

    vector<array<int,8>> nbr;
    vector<uint8_t> deg0;
    vector<uint8_t> edgeDist;

    vector<uint8_t> visited;
    vector<uint8_t> dyn;

    inline int id(int r, int c) const { return r * N + c; }
    inline int rowOf(int v) const { return v / N; }
    inline int colOf(int v) const { return v % N; }

    void buildGraph() {
        M = N * N;
        nbr.assign(M, {});
        deg0.assign(M, 0);
        edgeDist.assign(M, 0);

        for (int r = 0; r < N; ++r) {
            for (int c = 0; c < N; ++c) {
                int v = id(r,c);
                int k = 0;
                for (int t = 0; t < 8; ++t) {
                    int nr = r + KDR[t], nc = c + KDC[t];
                    if (0 <= nr && nr < N && 0 <= nc && nc < N) {
                        nbr[v][k++] = id(nr, nc);
                    }
                }
                deg0[v] = (uint8_t)k;
                int d = min(min(r, c), min(N - 1 - r, N - 1 - c));
                edgeDist[v] = (uint8_t)d;
                for (; k < 8; ++k) nbr[v][k] = -1;
            }
        }
    }

    inline void resetState() {
        visited.assign(M, 0);
        dyn = deg0;
    }

    inline void markVisited(int v) {
        visited[v] = 1;
        uint8_t dv = deg0[v];
        for (int i = 0; i < dv; ++i) {
            int u = nbr[v][i];
            if (!visited[u]) {
                if (dyn[u] > 0) --dyn[u];
            }
        }
    }

    inline uint8_t secondMinDegree(int u) const {
        uint8_t du = deg0[u];
        uint8_t best = 9;
        for (int i = 0; i < du; ++i) {
            int w = nbr[u][i];
            if (!visited[w]) best = min(best, dyn[w]);
        }
        return best;
    }

    vector<int> greedyAttempt(uint64_t seed) {
        resetState();
        XorShift64 rng(seed);

        vector<int> path;
        path.reserve((size_t)target);

        int cur = startId;
        path.push_back(cur);
        markVisited(cur);

        while ((int)path.size() < target) {
            int remaining = target - (int)path.size();
            int bestU = -1;
            int bestD1 = 100, bestD2 = 100, bestEdge = 100;
            uint64_t bestRnd = 0;

            uint8_t dcur = deg0[cur];
            // First pass: find best with avoiding dyn==0 early
            for (int i = 0; i < dcur; ++i) {
                int u = nbr[cur][i];
                if (visited[u]) continue;

                int d1 = (int)dyn[u];
                if (remaining > 1 && d1 == 0) d1 = 9; // avoid dead-end unless last step

                int d2 = (int)secondMinDegree(u);
                int ed = (int)edgeDist[u];
                uint64_t rr = rng.nextU64();

                if (d1 < bestD1 ||
                    (d1 == bestD1 && (d2 < bestD2 ||
                    (d2 == bestD2 && (ed < bestEdge ||
                    (ed == bestEdge && rr < bestRnd)))))) {
                    bestD1 = d1;
                    bestD2 = d2;
                    bestEdge = ed;
                    bestRnd = rr;
                    bestU = u;
                }
            }

            if (bestU == -1) break;

            cur = bestU;
            path.push_back(cur);
            markVisited(cur);
        }

        return path;
    }

    bool dfsTour(int cur, int depth, vector<int>& path, vector<int>& changedStack, vector<int>& changedMark, int markStamp) {
        if (depth == target) return true;

        // Collect candidates
        int cand[8];
        int cc = 0;
        uint8_t dcur = deg0[cur];
        for (int i = 0; i < dcur; ++i) {
            int u = nbr[cur][i];
            if (!visited[u]) cand[cc++] = u;
        }
        if (cc == 0) return false;

        // Sort by dyn then secondMin then edgeDist
        auto key = [&](int u) {
            int d1 = (int)dyn[u];
            int remaining = target - depth;
            if (remaining > 1 && d1 == 0) d1 = 9;
            int d2 = (int)secondMinDegree(u);
            int ed = (int)edgeDist[u];
            return tuple<int,int,int>(d1, d2, ed);
        };
        sort(cand, cand + cc, [&](int a, int b) {
            return key(a) < key(b);
        });

        for (int idx = 0; idx < cc; ++idx) {
            int u = cand[idx];
            // move to u
            visited[u] = 1;
            path.push_back(u);

            uint8_t du = deg0[u];
            int baseSize = (int)changedStack.size();
            for (int i = 0; i < du; ++i) {
                int w = nbr[u][i];
                if (!visited[w]) {
                    if (changedMark[w] != markStamp) {
                        changedMark[w] = markStamp;
                        changedStack.push_back(w);
                    }
                    if (dyn[w] > 0) --dyn[w];
                }
            }

            if (dfsTour(u, depth + 1, path, changedStack, changedMark, markStamp + 1)) return true;

            // undo degree changes from u
            for (int i = baseSize; i < (int)changedStack.size(); ++i) {
                int w = changedStack[i];
                // We decremented dyn[w] exactly once in this frame (possibly multiple times across siblings but tracked by markStamp mechanism)
                // But because we used markStamp, each frame has distinct stamp, so revert exactly once.
                ++dyn[w];
            }
            changedStack.resize(baseSize);

            visited[u] = 0;
            path.pop_back();
        }
        return false;
    }

    vector<int> solve() {
        buildGraph();
        startId = id(sr, sc);

        if (N % 2 == 0) target = M;
        else {
            int parity = ( (sr + 1) + (sc + 1) ) & 1; // using 1-indexed parity, same as 0-indexed
            if (parity == 0) target = M;
            else target = M - 1;
        }

        // Small N: backtracking to reach target (usually fast)
        if (N <= 10) {
            resetState();
            vector<int> path;
            path.reserve((size_t)target);
            path.push_back(startId);
            markVisited(startId);

            vector<int> changedStack;
            changedStack.reserve(8 * target);
            vector<int> changedMark(M, -1);
            // We need a different markStamp per recursion depth; just pass increasing stamps.
            // Since changedMark uses stamp values, ensure stamp never conflicts across different nodes; depth <= 100.
            int stamp0 = 1;

            if (dfsTour(startId, 1, path, changedStack, changedMark, stamp0)) return path;
            // Fall back if not found (should be rare)
        }

        // Greedy with restarts
        int attempts;
        if (N <= 50) attempts = 250;
        else if (N <= 120) attempts = 80;
        else if (N <= 240) attempts = 25;
        else attempts = 6;

        vector<int> best;
        best.reserve((size_t)target);

        uint64_t baseSeed = 0x9e3779b97f4a7c15ull;
        baseSeed ^= (uint64_t)N * 1315423911ull;
        baseSeed ^= (uint64_t)(sr + 1) * 2654435761ull;
        baseSeed ^= (uint64_t)(sc + 1) * 97531ull;

        for (int a = 0; a < attempts; ++a) {
            uint64_t seed = baseSeed ^ (uint64_t)a * 0xD1B54A32D192ED03ull;
            auto path = greedyAttempt(seed);
            if (path.size() > best.size()) best = std::move(path);
            if ((int)best.size() == target) break;
        }

        return best;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;
    int r, c;
    cin >> r >> c;
    --r; --c;

    Solver solver;
    solver.N = N;
    solver.sr = r;
    solver.sc = c;

    vector<int> path = solver.solve();

    FastOutput out;
    // Reserve roughly: first line + path lines
    size_t est = 32ull + (size_t)path.size() * 12ull;
    out.buf.reserve(est);

    out.pushInt((int)path.size());
    out.pushChar('\n');
    for (size_t i = 0; i < path.size(); ++i) {
        int v = path[i];
        int rr = v / N + 1;
        int cc = v % N + 1;
        out.pushInt(rr);
        out.pushChar(' ');
        out.pushInt(cc);
        if (i + 1 != path.size()) out.pushChar('\n');
    }
    out.flush();
    return 0;
}