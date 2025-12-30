#include <bits/stdc++.h>
using namespace std;

struct SplitMix64 {
    uint64_t x;
    explicit SplitMix64(uint64_t seed = 0) : x(seed) {}
    inline uint64_t next() {
        uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    inline uint32_t nextU32(uint32_t mod) { return (uint32_t)(next() % mod); }
};

static inline void appendInt(string &s, int x) {
    char buf[16];
    int n = 0;
    if (x == 0) buf[n++] = '0';
    else {
        char tmp[16];
        int m = 0;
        while (x > 0) {
            tmp[m++] = char('0' + (x % 10));
            x /= 10;
        }
        while (m--) buf[n++] = tmp[m];
    }
    s.append(buf, buf + n);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    cin >> N;
    int r0, c0;
    cin >> r0 >> c0;
    --r0; --c0;

    const int M = N * N;
    auto idx = [N](int r, int c) -> int { return r * N + c; };

    // Precompute neighbors
    vector<uint32_t> nb((size_t)M * 8);
    vector<uint8_t> cnt(M, 0);

    static const int dr[8] = {-2,-2,-1,-1, 1, 1, 2, 2};
    static const int dc[8] = {-1, 1,-2, 2,-2, 2,-1, 1};

    for (int r = 0; r < N; ++r) {
        for (int c = 0; c < N; ++c) {
            int v = idx(r, c);
            uint8_t k = 0;
            for (int t = 0; t < 8; ++t) {
                int nr = r + dr[t], nc = c + dc[t];
                if ((unsigned)nr < (unsigned)N && (unsigned)nc < (unsigned)N) {
                    nb[(size_t)v * 8 + k] = (uint32_t)idx(nr, nc);
                    ++k;
                }
            }
            cnt[v] = k;
        }
    }

    const int start = idx(r0, c0);

    int targetLen;
    bool startMajor = true;
    if (N % 2 == 0) {
        targetLen = M;
    } else {
        // Majority color is parity of (1,1) which is even (0 in 0-based parity).
        // In 0-based, (r+c)%2 == 0 corresponds to (1,1) color.
        startMajor = ((r0 + c0) % 2 == 0);
        targetLen = startMajor ? M : (M - 1);
    }

    vector<uint8_t> vis(M);
    vector<uint8_t> deg(M);

    auto run = [&](uint64_t seed, int forbid) -> vector<uint32_t> {
        memset(vis.data(), 0, (size_t)M);
        memcpy(deg.data(), cnt.data(), (size_t)M);

        if (forbid >= 0) {
            vis[forbid] = 1;
            uint8_t kf = cnt[forbid];
            size_t base = (size_t)forbid * 8;
            for (uint8_t i = 0; i < kf; ++i) {
                int u = (int)nb[base + i];
                if (!vis[u] && deg[u] > 0) --deg[u];
            }
        }

        if (vis[start]) return {};

        SplitMix64 rng(seed);

        vector<uint32_t> path;
        path.reserve((size_t)targetLen);

        int cur = start;
        bool useLookahead = (N < 200);

        for (int step = 0; step < targetLen; ++step) {
            if (vis[cur]) break;
            vis[cur] = 1;
            path.push_back((uint32_t)cur);

            // Update degrees of unvisited neighbors
            uint8_t kc = cnt[cur];
            size_t basec = (size_t)cur * 8;
            for (uint8_t i = 0; i < kc; ++i) {
                int u = (int)nb[basec + i];
                if (!vis[u] && deg[u] > 0) --deg[u];
            }

            if ((int)path.size() == targetLen) break;

            // Collect candidates with min degree
            int cand[8];
            int candN = 0;
            int minDeg = 100;

            for (uint8_t i = 0; i < kc; ++i) {
                int u = (int)nb[basec + i];
                if (vis[u]) continue;
                int d = (int)deg[u];
                if (d < minDeg) {
                    minDeg = d;
                    candN = 0;
                    cand[candN++] = u;
                } else if (d == minDeg) {
                    cand[candN++] = u;
                }
            }

            if (candN == 0) break;

            int chosen = cand[rng.nextU32((uint32_t)candN)];

            if (useLookahead && candN > 1) {
                int bestScore = INT_MAX;
                int bestList[8];
                int bestN = 0;

                for (int i = 0; i < candN; ++i) {
                    int u = cand[i];
                    int score = 0;
                    uint8_t ku = cnt[u];
                    size_t baseu = (size_t)u * 8;
                    for (uint8_t j = 0; j < ku; ++j) {
                        int w = (int)nb[baseu + j];
                        if (!vis[w]) score += (int)deg[w];
                    }
                    // slight randomized perturbation to diversify
                    score = score * 16 + (int)(rng.next() & 15ULL);

                    if (score < bestScore) {
                        bestScore = score;
                        bestN = 0;
                        bestList[bestN++] = u;
                    } else if (score == bestScore) {
                        bestList[bestN++] = u;
                    }
                }
                chosen = bestList[rng.nextU32((uint32_t)bestN)];
            }

            cur = chosen;
        }

        return path;
    };

    vector<int> forbids;
    forbids.push_back(-1);
    if (N % 2 == 1 && !startMajor) {
        forbids.clear();
        // Try omitting different majority-color corners to improve chance.
        forbids.push_back(idx(0, 0));
        forbids.push_back(idx(0, N - 1));
        forbids.push_back(idx(N - 1, 0));
        forbids.push_back(idx(N - 1, N - 1));
    }

    auto tStart = chrono::steady_clock::now();
    const double timeLimitSec = 0.92;

    vector<uint32_t> bestPath;
    bestPath.reserve((size_t)targetLen);

    uint64_t baseSeed = (uint64_t)N * 1315423911ULL ^ (uint64_t)(r0 + 1) * 2654435761ULL ^ (uint64_t)(c0 + 1) * 97531ULL;

    int maxTriesBase;
    if (N >= 300) maxTriesBase = 4;
    else if (N >= 150) maxTriesBase = 8;
    else if (N >= 80) maxTriesBase = 20;
    else if (N >= 50) maxTriesBase = 60;
    else maxTriesBase = 400;

    bool done = false;

    for (int forbid : forbids) {
        if (forbid == start) continue;
        for (int attempt = 0; attempt < maxTriesBase; ++attempt) {
            auto now = chrono::steady_clock::now();
            double elapsed = chrono::duration<double>(now - tStart).count();
            if (elapsed > timeLimitSec) break;

            uint64_t seed = baseSeed + (uint64_t)attempt * 0x9e3779b97f4a7c15ULL + (uint64_t)(forbid + 1) * 0xbf58476d1ce4e5b9ULL;
            vector<uint32_t> path = run(seed, forbid);

            if (path.size() > bestPath.size()) bestPath.swap(path);
            if ((int)bestPath.size() == targetLen) { done = true; break; }
        }
        if (done) break;
    }

    if (bestPath.empty()) {
        bestPath.push_back((uint32_t)start);
    }

    // Output
    string out;
    out.reserve((size_t)bestPath.size() * 8 + 64);

    appendInt(out, (int)bestPath.size());
    out.push_back('\n');

    for (size_t i = 0; i < bestPath.size(); ++i) {
        int v = (int)bestPath[i];
        int r = v / N + 1;
        int c = v % N + 1;
        appendInt(out, r);
        out.push_back(' ');
        appendInt(out, c);
        if (i + 1 < bestPath.size()) out.push_back('\n');
    }

    cout << out;
    return 0;
}