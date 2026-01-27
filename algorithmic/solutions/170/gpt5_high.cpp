#include <bits/stdc++.h>
using namespace std;

// Hungarian algorithm for square cost matrix (minimization)
vector<int> hungarian(const vector<vector<long long>>& a) {
    int n = (int)a.size();
    vector<long long> u(n + 1), v(n + 1);
    vector<int> p(n + 1), way(n + 1);
    const long long INF = (1LL<<60);
    for (int i = 1; i <= n; i++) {
        p[0] = i;
        int j0 = 0;
        vector<long long> minv(n + 1, INF);
        vector<char> used(n + 1, false);
        do {
            used[j0] = true;
            int i0 = p[j0], j1 = 0;
            long long delta = INF;
            for (int j = 1; j <= n; j++) if (!used[j]) {
                long long cur = a[i0 - 1][j - 1] - u[i0] - v[j];
                if (cur < minv[j]) minv[j] = cur, way[j] = j0;
                if (minv[j] < delta) delta = minv[j], j1 = j;
            }
            for (int j = 0; j <= n; j++) {
                if (used[j]) u[p[j]] += delta, v[j] -= delta;
                else minv[j] -= delta;
            }
            j0 = j1;
        } while (p[j0] != 0);
        do {
            int j1 = way[j0];
            p[j0] = p[j1];
            j0 = j1;
        } while (j0);
    }
    vector<int> ans(n, -1);
    for (int j = 1; j <= n; j++) if (p[j] != 0) ans[p[j] - 1] = j - 1;
    return ans;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    long long L;
    if (!(cin >> N >> L)) return 0;
    vector<int> T(N);
    for (int i = 0; i < N; i++) cin >> T[i];

    // Build cost matrix for assignment: minimize sum max(0, T_i - 2*T_j)
    // Add small tie-breaker preferring near i+1 to get a "nice" ring when equal.
    const long long SCALE = 1000; // scale to make base dominate tie-breaker
    vector<vector<long long>> cost(N, vector<long long>(N, 0));
    auto baseCost = [&](int i, int j)->long long {
        long long b = (long long)T[i] - 2LL * (long long)T[j];
        return b > 0 ? b : 0;
    };
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            long long base = baseCost(i, j);
            int dist = (j - (i + 1) + N) % N; // prefer j == i+1
            cost[i][j] = base * SCALE + dist;
        }
    }

    // Initial permutation succ via Hungarian
    vector<int> succ = hungarian(cost);

    // Merge cycles into a single cycle by swapping successors across cycles
    auto get_cycles = [&](const vector<int>& s)->vector<vector<int>>{
        vector<vector<int>> cycles;
        vector<char> vis(N, false);
        for (int i = 0; i < N; i++) if (!vis[i]) {
            int x = i;
            vector<int> cyc;
            while (!vis[x]) { vis[x] = true; cyc.push_back(x); x = s[x]; }
            cycles.push_back(cyc);
        }
        return cycles;
    };

    vector<vector<int>> cycles = get_cycles(succ);
    // Prepare baseCost quick access
    while ((int)cycles.size() > 1) {
        // Use the first cycle as base, connect it with any other cycle with minimal delta
        vector<char> inA(N, false);
        for (int x : cycles[0]) inA[x] = true;
        long long bestDelta = (1LL<<60);
        int bi = -1, bk = -1;
        for (int i : cycles[0]) {
            for (int k = 0; k < N; k++) if (!inA[k]) {
                int Si = succ[i];
                int Sk = succ[k];
                long long delta = baseCost(i, Sk) + baseCost(k, Si) - baseCost(i, Si) - baseCost(k, Sk);
                if (delta < bestDelta) {
                    bestDelta = delta;
                    bi = i; bk = k;
                }
            }
        }
        if (bi == -1 || bk == -1) break; // should not happen
        // Swap successors of bi and bk
        int Si = succ[bi];
        int Sk = succ[bk];
        succ[bi] = Sk;
        succ[bk] = Si;
        cycles = get_cycles(succ);
    }

    // Build prev mapping from succ (permutation)
    vector<int> prev(N, -1);
    for (int i = 0; i < N; i++) prev[succ[i]] = i;

    // Compute R_j = 2*T_j - T_prev(j)
    vector<long long> R(N);
    for (int j = 0; j < N; j++) {
        R[j] = 2LL * T[j] - (long long)T[prev[j]];
    }

    // Assign second edges f(i) to bins j to match R as closely as possible
    vector<long long> y(N, 0); // current assigned sum to bin j
    vector<int> f(N, 0);
    vector<int> idx(N);
    iota(idx.begin(), idx.end(), 0);
    sort(idx.begin(), idx.end(), [&](int a, int b){ return T[a] > T[b]; });

    auto incr = [&](long long yj, long long Rj, long long w)->long long{
        return llabs((yj + w) - Rj) - llabs(yj - Rj);
    };

    for (int ii = 0; ii < N; ii++) {
        int i = idx[ii];
        long long w = T[i];
        long long bestD = (1LL<<60);
        int bestJ = 0;
        for (int j = 0; j < N; j++) {
            long long d = incr(y[j], R[j], w);
            if (d < bestD) {
                bestD = d;
                bestJ = j;
            }
        }
        f[i] = bestJ;
        y[bestJ] += w;
    }

    // Local improvement: try single-node moves to reduce total absolute difference
    auto totalError = [&]()->long long{
        long long s = 0;
        for (int j = 0; j < N; j++) s += llabs(y[j] - R[j]);
        return s;
    };

    for (int pass = 0; pass < 3; pass++) {
        bool improved = false;
        for (int ii = 0; ii < N; ii++) {
            int i = idx[ii];
            long long w = T[i];
            if (w == 0) continue;
            int oldJ = f[i];
            long long cur = llabs(y[oldJ] - R[oldJ]);
            long long bestDelta = 0;
            int bestJ = oldJ;
            for (int j = 0; j < N; j++) if (j != oldJ) {
                long long delta = 0;
                // remove from oldJ, add to j
                delta += llabs((y[oldJ] - w) - R[oldJ]) - llabs(y[oldJ] - R[oldJ]);
                delta += llabs((y[j] + w) - R[j]) - llabs(y[j] - R[j]);
                if (delta < bestDelta) {
                    bestDelta = delta;
                    bestJ = j;
                }
            }
            if (bestJ != oldJ) {
                y[oldJ] -= w;
                y[bestJ] += w;
                f[i] = bestJ;
                improved = true;
            }
        }
        if (!improved) break;
    }

    // Output a_i and b_i
    // Choose a_i = succ[i] (ring edge), b_i = f[i] (balancing edge)
    for (int i = 0; i < N; i++) {
        int ai = succ[i];
        int bi = f[i];
        cout << ai << " " << bi << "\n";
    }
    return 0;
}