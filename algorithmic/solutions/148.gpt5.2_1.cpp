#include <bits/stdc++.h>
using namespace std;

static constexpr int H = 50;
static constexpr int W = 50;
static constexpr int V = H * W;

struct RNG {
    uint64_t x;
    explicit RNG(uint64_t seed = 88172645463325252ULL) : x(seed) {}
    inline uint64_t nextU64() {
        x ^= x << 7;
        x ^= x >> 9;
        return x;
    }
    inline uint32_t nextU32() { return (uint32_t)nextU64(); }
    inline int nextInt(int mod) { return (int)(nextU64() % (uint64_t)mod); }
    inline double nextDouble() { // [0,1)
        return (nextU64() >> 11) * (1.0 / 9007199254740992.0);
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int si, sj;
    cin >> si >> sj;

    vector<int> tile(V);
    int maxTile = -1;
    for (int i = 0; i < H; i++) {
        for (int j = 0; j < W; j++) {
            int t;
            cin >> t;
            tile[i * W + j] = t;
            maxTile = max(maxTile, t);
        }
    }
    int M = maxTile + 1;

    vector<int> val(V);
    for (int i = 0; i < H; i++) {
        for (int j = 0; j < W; j++) {
            int p;
            cin >> p;
            val[i * W + j] = p;
        }
    }

    vector<array<int, 4>> adj(V);
    vector<int> deg(V, 0);
    for (int i = 0; i < H; i++) {
        for (int j = 0; j < W; j++) {
            int v = i * W + j;
            int d = 0;
            auto add = [&](int ni, int nj) {
                if (ni < 0 || ni >= H || nj < 0 || nj >= W) return;
                int u = ni * W + nj;
                if (tile[u] == tile[v]) return;
                adj[v][d++] = u;
            };
            add(i - 1, j);
            add(i + 1, j);
            add(i, j - 1);
            add(i, j + 1);
            deg[v] = d;
            for (int k = d; k < 4; k++) adj[v][k] = -1;
        }
    }

    int start = si * W + sj;

    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    seed ^= (uint64_t)(uintptr_t)(&seed);
    RNG rng(seed);

    vector<int> seen(M, 0);
    int stamp = 1;
    auto newStamp = [&]() {
        stamp++;
        if (stamp == INT_MAX) {
            fill(seen.begin(), seen.end(), 0);
            stamp = 1;
        }
    };

    auto chooseNext = [&](int cur, double noise, double wdeg, double w2) -> int {
        int bestU = -1;
        double bestE = -1e100;
        for (int k = 0; k < deg[cur]; k++) {
            int u = adj[cur][k];
            if (u < 0) continue;
            int tid = tile[u];
            if (seen[tid] == stamp) continue;

            int d2 = 0;
            int best2 = 0;
            for (int kk = 0; kk < deg[u]; kk++) {
                int w = adj[u][kk];
                if (w < 0) continue;
                int tw = tile[w];
                if (seen[tw] == stamp) continue;
                d2++;
                best2 = max(best2, val[w]);
            }

            double e = (double)val[u] + wdeg * (double)d2 + w2 * (double)best2;
            e += rng.nextDouble() * noise;

            if (e > bestE) {
                bestE = e;
                bestU = u;
            }
        }
        return bestU;
    };

    auto rolloutFromPrefix = [&](const vector<int>& basePath, int cutIdx, double noise, double wdeg, double w2) -> pair<vector<int>, int> {
        newStamp();

        vector<int> path;
        path.resize(cutIdx + 1);
        for (int i = 0; i <= cutIdx; i++) path[i] = basePath[i];

        int score = 0;
        for (int i = 0; i <= cutIdx; i++) {
            int v = path[i];
            score += val[v];
            seen[tile[v]] = stamp;
        }

        int cur = path.back();
        while ((int)path.size() < V) {
            int nxt = chooseNext(cur, noise, wdeg, w2);
            if (nxt < 0) break;
            seen[tile[nxt]] = stamp;
            path.push_back(nxt);
            score += val[nxt];
            cur = nxt;
        }
        return {path, score};
    };

    auto rolloutFromStart = [&](double noise, double wdeg, double w2) -> pair<vector<int>, int> {
        vector<int> base(1, start);
        return rolloutFromPrefix(base, 0, noise, wdeg, w2);
    };

    auto rebuildPrefixSum = [&](const vector<int>& path) -> vector<int> {
        vector<int> pref(path.size());
        int s = 0;
        for (int i = 0; i < (int)path.size(); i++) {
            s += val[path[i]];
            pref[i] = s;
        }
        return pref;
    };

    vector<int> bestPath;
    int bestScore = -1;

    // Initial multi-start
    for (int it = 0; it < 60; it++) {
        double noise = 25.0 + 25.0 * rng.nextDouble();
        auto [p, sc] = rolloutFromStart(noise, 12.0, 0.25);
        if (sc > bestScore) {
            bestScore = sc;
            bestPath = std::move(p);
        }
    }

    vector<int> curPath = bestPath;
    int curScore = bestScore;
    vector<int> curPref = rebuildPrefixSum(curPath);

    auto t0 = chrono::steady_clock::now();
    const double TL = 1.95;
    const double T_start = 2500.0;
    const double T_end = 30.0;

    vector<int> candPath;
    while (true) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - t0).count();
        if (elapsed >= TL) break;
        double progress = elapsed / TL;
        double temp = T_start + (T_end - T_start) * progress;
        double noise = 30.0 + (1.0 - progress) * 70.0;

        int L = (int)curPath.size();
        int cutIdx;
        if (L <= 1) {
            cutIdx = 0;
        } else {
            if (rng.nextDouble() < 0.07) cutIdx = 0;
            else cutIdx = rng.nextInt(L);
        }

        double wdeg = 10.0 + 8.0 * (1.0 - progress);
        double w2 = 0.20 + 0.10 * (1.0 - progress);

        auto [np, nsc] = rolloutFromPrefix(curPath, cutIdx, noise, wdeg, w2);
        int diff = nsc - curScore;

        bool accept = false;
        if (diff >= 0) accept = true;
        else {
            double prob = exp((double)diff / temp);
            if (rng.nextDouble() < prob) accept = true;
        }

        if (accept) {
            curPath = std::move(np);
            curScore = nsc;
            curPref = rebuildPrefixSum(curPath);
        }

        if (curScore > bestScore) {
            bestScore = curScore;
            bestPath = curPath;
        }
    }

    string out;
    out.reserve(max(0, (int)bestPath.size() - 1));
    for (int i = 0; i + 1 < (int)bestPath.size(); i++) {
        int a = bestPath[i];
        int b = bestPath[i + 1];
        int da = b - a;
        if (da == -W) out.push_back('U');
        else if (da == W) out.push_back('D');
        else if (da == -1) out.push_back('L');
        else if (da == 1) out.push_back('R');
        else {
            // Fallback (should not happen)
        }
    }
    cout << out << "\n";
    return 0;
}