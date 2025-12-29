#include <bits/stdc++.h>
using namespace std;

struct FastOutput {
    string buf;
    FastOutput() { buf.reserve(8 * 1024 * 1024); }
    inline void pushChar(char c) { buf.push_back(c); }
    inline void pushInt(int x) {
        if (x == 0) { buf.push_back('0'); return; }
        char s[16];
        int n = 0;
        while (x > 0) { s[n++] = char('0' + (x % 10)); x /= 10; }
        while (n--) buf.push_back(s[n]);
    }
    inline void pushStr(const char* s) { while (*s) buf.push_back(*s++); }
    void flush() {
        fwrite(buf.data(), 1, buf.size(), stdout);
    }
};

static inline uint64_t splitmix64(uint64_t &x) {
    uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}

struct Solver {
    int N = 0;
    int N2 = 0;
    vector<int> off;
    vector<int> to;
    vector<uint8_t> initDeg;

    vector<uint32_t> prio;
    vector<uint8_t> visited;
    vector<uint8_t> deg;

    vector<int> path;
    vector<uint8_t> tried;

    int zeroCount = 0;
    int initialZeroCount = 0;

    void buildGraph() {
        N2 = N * N;
        off.assign(N2 + 1, 0);
        to.clear();
        to.reserve((size_t)N2 * 8);

        static const int dr[8] = {+2, +2, +1, +1, -1, -1, -2, -2};
        static const int dc[8] = {+1, -1, +2, -2, +2, -2, +1, -1};

        int ptr = 0;
        off[0] = 0;
        for (int v = 0; v < N2; v++) {
            off[v] = ptr;
            int r = v / N;
            int c = v % N;
            for (int k = 0; k < 8; k++) {
                int rr = r + dr[k], cc = c + dc[k];
                if ((unsigned)rr < (unsigned)N && (unsigned)cc < (unsigned)N) {
                    to.push_back(rr * N + cc);
                    ptr++;
                }
            }
            off[v + 1] = ptr;
        }

        initDeg.assign(N2, 0);
        initialZeroCount = 0;
        for (int v = 0; v < N2; v++) {
            uint8_t d = (uint8_t)(off[v + 1] - off[v]);
            initDeg[v] = d;
            if (d == 0) initialZeroCount++;
        }

        prio.assign(N2, 0);
        visited.assign(N2, 0);
        deg.assign(N2, 0);
        path.reserve(N2);
        tried.reserve(N2);
    }

    void genPrio(uint64_t seed) {
        uint64_t x = seed;
        for (int i = 0; i < N2; i++) {
            prio[i] = (uint32_t)splitmix64(x);
        }
    }

    inline void visitVertex(int v) {
        // v must be unvisited
        if (deg[v] == 0) zeroCount--;
        visited[v] = 1;
        for (int ei = off[v]; ei < off[v + 1]; ei++) {
            int u = to[ei];
            if (!visited[u]) {
                if (deg[u] == 1) zeroCount++;
                deg[u]--;
            }
        }
    }

    inline void unvisitVertex(int v) {
        // v must be visited
        visited[v] = 0;
        for (int ei = off[v]; ei < off[v + 1]; ei++) {
            int u = to[ei];
            if (!visited[u]) {
                if (deg[u] == 0) zeroCount--;
                deg[u]++;
            }
        }
        uint8_t dv = 0;
        for (int ei = off[v]; ei < off[v + 1]; ei++) {
            int u = to[ei];
            if (!visited[u]) dv++;
        }
        deg[v] = dv;
        if (dv == 0) zeroCount++;
    }

    bool solveFromStart(int startIdx, chrono::steady_clock::time_point deadline, long long backtrackLimit) {
        memset(visited.data(), 0, (size_t)N2);
        memcpy(deg.data(), initDeg.data(), (size_t)N2);
        zeroCount = initialZeroCount;

        path.clear();
        tried.clear();

        visitVertex(startIdx);
        path.push_back(startIdx);
        tried.push_back(0);

        long long backtracks = 0;
        long long steps = 0;

        while ((int)path.size() < N2) {
            if ((steps & 4095LL) == 0) {
                if (chrono::steady_clock::now() > deadline) return false;
            }
            steps++;

            int remaining = N2 - (int)path.size();
            if (zeroCount > 0 && remaining > 1) {
                // must backtrack
                if (path.size() == 1) return false;
                int v = path.back();
                unvisitVertex(v);
                path.pop_back();
                tried.pop_back();
                backtracks++;
                if (backtracks > backtrackLimit) return false;
                continue;
            }

            int v = path.back();
            uint8_t &mask = tried.back();
            int base = off[v];
            int cnt = off[v + 1] - base;

            int bestU = -1, bestK = -1;
            int bestD = 1000000000;
            int bestSum = 1000000000;
            uint32_t bestP = 0xffffffffu;

            bool lastMove = ((int)path.size() + 1 == N2);

            for (int k = 0; k < cnt; k++) {
                if (mask & (uint8_t)(1u << k)) continue;
                int u = to[base + k];
                if (visited[u]) continue;
                uint8_t du = deg[u];
                if (!lastMove && du == 0) continue;

                int sum = 0;
                for (int ei = off[u]; ei < off[u + 1]; ei++) {
                    int w = to[ei];
                    if (!visited[w]) sum += (int)deg[w];
                }
                uint32_t p = prio[u];

                if ((int)du < bestD ||
                    ((int)du == bestD && sum < bestSum) ||
                    ((int)du == bestD && sum == bestSum && p < bestP)) {
                    bestD = (int)du;
                    bestSum = sum;
                    bestP = p;
                    bestU = u;
                    bestK = k;
                }
            }

            if (bestU == -1) {
                if (path.size() == 1) return false;
                int cur = path.back();
                unvisitVertex(cur);
                path.pop_back();
                tried.pop_back();
                backtracks++;
                if (backtracks > backtrackLimit) return false;
                continue;
            }

            mask |= (uint8_t)(1u << bestK);
            visitVertex(bestU);
            path.push_back(bestU);
            tried.push_back(0);
        }
        return true;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;
    int r0, c0;
    cin >> r0 >> c0;
    int startIdx = (r0 - 1) * N + (c0 - 1);

    Solver solver;
    solver.N = N;
    solver.buildGraph();

    auto t0 = chrono::steady_clock::now();
    auto deadline = t0 + chrono::milliseconds(900);

    vector<int> bestPath;
    bestPath.reserve(solver.N2);

    bool ok = false;
    for (int attempt = 0; attempt < 64; attempt++) {
        if (chrono::steady_clock::now() > deadline) break;

        uint64_t seed = 0x123456789abcdefULL;
        seed ^= (uint64_t)N * 1000003ULL;
        seed ^= (uint64_t)r0 * 10007ULL;
        seed ^= (uint64_t)c0 * 10009ULL;
        seed ^= (uint64_t)attempt * 0x9e3779b97f4a7c15ULL;

        solver.genPrio(seed);

        long long backtrackLimit = (N <= 12 ? 5000000LL : (long long)solver.N2 * 8LL);
        ok = solver.solveFromStart(startIdx, deadline, backtrackLimit);
        if ((int)solver.path.size() > (int)bestPath.size()) bestPath = solver.path;
        if (ok && (int)solver.path.size() == solver.N2) {
            bestPath = solver.path;
            break;
        }
    }

    if ((int)bestPath.size() < 1) {
        bestPath.push_back(startIdx);
    }

    FastOutput out;
    out.pushInt((int)bestPath.size());
    out.pushChar('\n');
    for (size_t i = 0; i < bestPath.size(); i++) {
        int v = bestPath[i];
        int r = v / N + 1;
        int c = v % N + 1;
        out.pushInt(r);
        out.pushChar(' ');
        out.pushInt(c);
        out.pushChar('\n');
    }
    out.flush();
    return 0;
}