#include <bits/stdc++.h>
using namespace std;

static inline int ask(int u, int v) {
    printf("? %d %d\n", u, v);
    fflush(stdout);
    int d;
    if (scanf("%d", &d) != 1) exit(0);
    return d;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if (!(cin >> n)) return 0;

    auto getDistances = [&](int src) {
        vector<int> d(n + 1, 0);
        for (int v = 1; v <= n; ++v) {
            if (v == src) { d[v] = 0; continue; }
            d[v] = ask(src, v);
        }
        return d;
    };

    // First, take s0 = 1
    int s0 = 1;
    vector<int> d_s0 = getDistances(s0);

    // Find t: farthest from s0
    int t = 1, maxd = -1;
    for (int i = 1; i <= n; ++i) {
        if (d_s0[i] > maxd) { maxd = d_s0[i]; t = i; }
    }

    // Distances from t
    vector<int> d_t = getDistances(t);

    // Find s: farthest from t (the other diameter endpoint)
    int s = 1; maxd = -1;
    for (int i = 1; i <= n; ++i) {
        if (d_t[i] > maxd) { maxd = d_t[i]; s = i; }
    }
    int D = d_t[s];

    // Distances from s
    vector<int> d_s = getDistances(s);

    // Prepare counts of x_w = (d_s[w] + D - d_t[w]) / 2
    // Also map position on path s-t to node id
    vector<int> pos2node(D + 1, -1);
    for (int i = 1; i <= n; ++i) {
        if (d_s[i] + d_t[i] == D) {
            int x = d_s[i];
            pos2node[x] = i;
        }
    }

    vector<long long> countX(D + 1, 0);
    vector<long long> sumX(D + 1, 0);

    long long sum_dt = 0;
    for (int i = 1; i <= n; ++i) {
        int xi = (d_s[i] + D - d_t[i]) / 2;
        if (xi < 0) xi = 0;
        if (xi > D) xi = D;
        countX[xi] += 1;
        sumX[xi] += xi;
        sum_dt += d_t[i];
    }

    long long sumB = sum_dt - 1LL * n * D;

    // Prefix sums for counts and sumX
    vector<long long> prefCount(D + 1, 0), prefSumX(D + 1, 0);
    long long totCount = 0, totSumX = 0;
    for (int x = 0; x <= D; ++x) {
        totCount += countX[x];
        totSumX += sumX[x];
        prefCount[x] = totCount;
        prefSumX[x] = totSumX;
    }

    auto count_gt = [&](int x) -> long long {
        // number with x_w > x
        if (x >= D) return 0;
        return totCount - prefCount[x];
    };
    auto sumX_gt = [&](int x) -> long long {
        // sum of x_w over those with x_w > x
        if (x >= D) return 0;
        return totSumX - prefSumX[x];
    };

    long long bestS = LLONG_MAX;
    int bestX = 0;
    for (int x = 0; x <= D; ++x) {
        if (pos2node[x] == -1) continue; // only actual path nodes
        long long cntg = count_gt(x);
        long long sumg = sumX_gt(x);
        long long Sx = sumB + 1LL * n * x + 2LL * sumg - 2LL * x * cntg;
        if (Sx < bestS) {
            bestS = Sx;
            bestX = x;
        }
    }

    int ans = pos2node[bestX];
    printf("! %d\n", ans);
    fflush(stdout);
    return 0;
}