#include <bits/stdc++.h>
using namespace std;

static const int H = 50, W = 50, N = H * W;

struct XorShift64 {
    uint64_t x;
    XorShift64(uint64_t seed = 88172645463325252ULL) : x(seed) {}
    inline uint64_t nextU64() {
        x ^= x << 7;
        x ^= x >> 9;
        return x;
    }
    inline uint32_t nextU32() { return (uint32_t)nextU64(); }
    inline int nextInt(int lo, int hi) { // inclusive
        return lo + (int)(nextU32() % (uint32_t)(hi - lo + 1));
    }
    inline double nextDouble() { // [0,1)
        return (nextU64() >> 11) * (1.0 / 9007199254740992.0);
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int si, sj;
    cin >> si >> sj;

    vector<int> tile(N), val(N);
    int maxT = -1;
    for (int i = 0; i < H; i++) {
        for (int j = 0; j < W; j++) {
            int t;
            cin >> t;
            tile[i * W + j] = t;
            maxT = max(maxT, t);
        }
    }
    for (int i = 0; i < H; i++) {
        for (int j = 0; j < W; j++) {
            int p;
            cin >> p;
            val[i * W + j] = p;
        }
    }
    int M = maxT + 1;

    int nxt[N][4];
    char dch[4] = {'U', 'D', 'L', 'R'};
    int di[4] = {-1, 1, 0, 0};
    int dj[4] = {0, 0, -1, 1};
    for (int i = 0; i < H; i++) {
        for (int j = 0; j < W; j++) {
            int id = i * W + j;
            for (int d = 0; d < 4; d++) {
                int ni = i + di[d], nj = j + dj[d];
                if (0 <= ni && ni < H && 0 <= nj && nj < W) nxt[id][d] = ni * W + nj;
                else nxt[id][d] = -1;
            }
        }
    }

    vector<int> stamp(M, 0);
    int runId = 0;

    auto start = chrono::high_resolution_clock::now();
    const double TL = 1.85;

    XorShift64 rng(chrono::high_resolution_clock::now().time_since_epoch().count());

    string bestPath;
    int bestScore = -1;

    int startId = si * W + sj;
    int startTile = tile[startId];

    while (true) {
        auto now = chrono::high_resolution_clock::now();
        double elapsed = chrono::duration<double>(now - start).count();
        if (elapsed > TL) break;

        runId++;
        if (runId == INT_MAX) {
            fill(stamp.begin(), stamp.end(), 0);
            runId = 1;
        }

        int cur = startId;
        stamp[startTile] = runId;
        int score = val[cur];
        string path;
        path.reserve(3000);

        // Randomize weights a bit per rollout
        double wMob = 12.0 + rng.nextDouble() * 22.0;   // 12..34
        double w2   = 0.15 + rng.nextDouble() * 0.55;   // 0.15..0.70
        double wDeg = 0.0 + rng.nextDouble() * 6.0;     // 0..6 (tiny extra)
        double noiseBase = 1.0 + rng.nextDouble() * 6.0;// 1..7

        while (true) {
            struct Cand { double sc; int d; int to; };
            Cand best[4];
            int cnt = 0;

            for (int d = 0; d < 4; d++) {
                int to = nxt[cur][d];
                if (to < 0) continue;
                int tt = tile[to];
                if (stamp[tt] == runId) continue;

                int mobility = 0;
                int best2 = 0;
                for (int d2 = 0; d2 < 4; d2++) {
                    int to2 = nxt[to][d2];
                    if (to2 < 0) continue;
                    int tt2 = tile[to2];
                    if (stamp[tt2] == runId) continue;
                    mobility++;
                    best2 = max(best2, val[to2]);
                }

                // degree-ish: count of unvisited tiles around destination's tile "boundary"
                // just reuse mobility, but with a slightly different weight
                double deg = (double)mobility;

                double sc = (double)val[to] + wMob * mobility + w2 * best2 + wDeg * deg;
                sc += (rng.nextDouble() - 0.5) * noiseBase;
                best[cnt++] = {sc, d, to};
            }

            if (cnt == 0) break;

            int pick = 0;
            if (cnt >= 2) {
                // pick among top candidates with a slight randomness
                int a = 0;
                for (int i = 1; i < cnt; i++) if (best[i].sc > best[a].sc) a = i;
                int b = -1;
                for (int i = 0; i < cnt; i++) if (i != a && (b < 0 || best[i].sc > best[b].sc)) b = i;

                double r = rng.nextDouble();
                if (r < 0.86) pick = a;
                else if (b >= 0 && r < 0.97) pick = b;
                else pick = rng.nextInt(0, cnt - 1);
            } else {
                pick = 0;
            }

            int to = best[pick].to;
            int d = best[pick].d;
            stamp[tile[to]] = runId;
            cur = to;
            score += val[cur];
            path.push_back(dch[d]);
        }

        if (score > bestScore) {
            bestScore = score;
            bestPath = path;
        }
    }

    cout << bestPath << "\n";
    return 0;
}