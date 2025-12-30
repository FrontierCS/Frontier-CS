#include <bits/stdc++.h>
using namespace std;

struct PairOp {
    char d;
    int p;
    int k;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    if(!(cin >> N)) return 0;
    vector<string> C(N);
    for (int i = 0; i < N; ++i) cin >> C[i];

    const int INF = 1e9;

    vector<vector<int>> isO(N, vector<int>(N, 0));
    vector<vector<int>> isX(N, vector<int>(N, 0));
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            isO[i][j] = (C[i][j] == 'o');
            isX[i][j] = (C[i][j] == 'x');
        }
    }

    // Precompute minimal plan per x (direction and k)
    struct MinPlan { char d; int p; int k; };
    vector<vector<MinPlan>> minPlan(N, vector<MinPlan>(N, {'?', -1, INF}));

    auto noOAbove = [&](int i, int j)->bool{
        for (int r = 0; r < i; ++r) if (isO[r][j]) return false;
        return true;
    };
    auto noOBelow = [&](int i, int j)->bool{
        for (int r = i+1; r < N; ++r) if (isO[r][j]) return false;
        return true;
    };
    auto noOLeft = [&](int i, int j)->bool{
        for (int c = 0; c < j; ++c) if (isO[i][c]) return false;
        return true;
    };
    auto noORight = [&](int i, int j)->bool{
        for (int c = j+1; c < N; ++c) if (isO[i][c]) return false;
        return true;
    };

    vector<pair<int,int>> xs;
    xs.reserve(2*N);
    for (int i = 0; i < N; ++i) for (int j = 0; j < N; ++j) if (isX[i][j]) xs.emplace_back(i,j);

    for (auto [i,j] : xs) {
        int bestk = INF; char bestd='?'; int bestp=-1;
        if (noOAbove(i,j)) {
            int k = i+1;
            if (k < bestk) { bestk = k; bestd = 'U'; bestp = j; }
        }
        if (noOBelow(i,j)) {
            int k = N - i;
            if (k < bestk) { bestk = k; bestd = 'D'; bestp = j; }
        }
        if (noOLeft(i,j)) {
            int k = j+1;
            if (k < bestk) { bestk = k; bestd = 'L'; bestp = i; }
        }
        if (noORight(i,j)) {
            int k = N - j;
            if (k < bestk) { bestk = k; bestd = 'R'; bestp = i; }
        }
        // At least one is guaranteed
        minPlan[i][j] = {bestd, bestp, bestk};
    }

    // Allowed k_max per line for aggregator
    vector<int> colUpKmax(N), colDownKmax(N), rowLeftKmax(N), rowRightKmax(N);
    for (int j = 0; j < N; ++j) {
        int firstO = N;
        for (int i = 0; i < N; ++i) if (isO[i][j]) { firstO = i; break; }
        int lastO = -1;
        for (int i = N-1; i >= 0; --i) if (isO[i][j]) { lastO = i; break; }
        colUpKmax[j] = firstO; // 0..firstO-1 is safe, so k in [1..firstO]
        colDownKmax[j] = (lastO == -1 ? N : N - lastO - 1);
    }
    for (int i = 0; i < N; ++i) {
        int firstO = N;
        for (int j = 0; j < N; ++j) if (isO[i][j]) { firstO = j; break; }
        int lastO = -1;
        for (int j = N-1; j >= 0; --j) if (isO[i][j]) { lastO = j; break; }
        rowLeftKmax[i] = firstO;
        rowRightKmax[i] = (lastO == -1 ? N : N - lastO - 1);
    }

    // remainMinSum is sum of k (not doubled) for remaining x by their minimal plans
    long long remainMinSum = 0;
    for (auto [i,j] : xs) remainMinSum += minPlan[i][j].k;

    vector<PairOp> chosenPairs; // store as pair operations with repetition k
    long long Tcount = 0; // actual moves count (each pair contributes 2*k)

    // Aggregator: choose operations with positive improvement (sum of min_k removed - k)
    while (true) {
        long long bestImpr = 0; // improvement measured in k-units
        char bestd = '?'; int bestp = -1; int bestk = 0;
        int bestGainCnt = 0;

        // U
        for (int j = 0; j < N; ++j) {
            int K = colUpKmax[j];
            for (int k = 1; k <= K; ++k) {
                long long G = 0; int gainCnt = 0;
                for (int r = 0; r < k; ++r) if (isX[r][j]) { G += minPlan[r][j].k; ++gainCnt; }
                long long impr = G - k;
                if (impr > bestImpr || (impr == bestImpr && (gainCnt > bestGainCnt || (gainCnt == bestGainCnt && k < bestk)))) {
                    if (gainCnt > 0) {
                        bestImpr = impr;
                        bestd = 'U'; bestp = j; bestk = k; bestGainCnt = gainCnt;
                    }
                }
            }
        }
        // D
        for (int j = 0; j < N; ++j) {
            int K = colDownKmax[j];
            for (int k = 1; k <= K; ++k) {
                long long G = 0; int gainCnt = 0;
                for (int r = N-k; r < N; ++r) if (isX[r][j]) { G += minPlan[r][j].k; ++gainCnt; }
                long long impr = G - k;
                if (impr > bestImpr || (impr == bestImpr && (gainCnt > bestGainCnt || (gainCnt == bestGainCnt && k < bestk)))) {
                    if (gainCnt > 0) {
                        bestImpr = impr;
                        bestd = 'D'; bestp = j; bestk = k; bestGainCnt = gainCnt;
                    }
                }
            }
        }
        // L
        for (int i = 0; i < N; ++i) {
            int K = rowLeftKmax[i];
            for (int k = 1; k <= K; ++k) {
                long long G = 0; int gainCnt = 0;
                for (int c = 0; c < k; ++c) if (isX[i][c]) { G += minPlan[i][c].k; ++gainCnt; }
                long long impr = G - k;
                if (impr > bestImpr || (impr == bestImpr && (gainCnt > bestGainCnt || (gainCnt == bestGainCnt && k < bestk)))) {
                    if (gainCnt > 0) {
                        bestImpr = impr;
                        bestd = 'L'; bestp = i; bestk = k; bestGainCnt = gainCnt;
                    }
                }
            }
        }
        // R
        for (int i = 0; i < N; ++i) {
            int K = rowRightKmax[i];
            for (int k = 1; k <= K; ++k) {
                long long G = 0; int gainCnt = 0;
                for (int c = N-k; c < N; ++c) if (isX[i][c]) { G += minPlan[i][c].k; ++gainCnt; }
                long long impr = G - k;
                if (impr > bestImpr || (impr == bestImpr && (gainCnt > bestGainCnt || (gainCnt == bestGainCnt && k < bestk)))) {
                    if (gainCnt > 0) {
                        bestImpr = impr;
                        bestd = 'R'; bestp = i; bestk = k; bestGainCnt = gainCnt;
                    }
                }
            }
        }

        if (bestImpr <= 0) break; // no beneficial operation

        // Apply best operation
        chosenPairs.push_back({bestd, bestp, bestk});
        Tcount += 2LL * bestk;

        // Remove x's covered and update remainMinSum
        if (bestd == 'U') {
            int j = bestp;
            for (int r = 0; r < bestk; ++r) if (isX[r][j]) { remainMinSum -= minPlan[r][j].k; isX[r][j] = 0; }
        } else if (bestd == 'D') {
            int j = bestp;
            for (int r = N - bestk; r < N; ++r) if (isX[r][j]) { remainMinSum -= minPlan[r][j].k; isX[r][j] = 0; }
        } else if (bestd == 'L') {
            int i = bestp;
            for (int c = 0; c < bestk; ++c) if (isX[i][c]) { remainMinSum -= minPlan[i][c].k; isX[i][c] = 0; }
        } else if (bestd == 'R') {
            int i = bestp;
            for (int c = N - bestk; c < N; ++c) if (isX[i][c]) { remainMinSum -= minPlan[i][c].k; isX[i][c] = 0; }
        }
    }

    // Fallback: remove remaining x individually by minimal plans, skipping already removed ones and leveraging collateral removal
    // We'll process alive 'x's until none remain
    // To speed up, collect alive x's iteratively
    auto anyXLeft = [&]()->bool{
        for (int i = 0; i < N; ++i) for (int j = 0; j < N; ++j) if (isX[i][j]) return true;
        return false;
    };

    while (anyXLeft()) {
        // find next alive x
        int si=-1, sj=-1;
        for (int i = 0; i < N; ++i) { for (int j = 0; j < N; ++j) if (isX[i][j]) { si=i; sj=j; break; } if (si!=-1) break; }
        auto mp = minPlan[si][sj];
        // Apply this minimal plan pair
        chosenPairs.push_back({mp.d, mp.p, mp.k});
        Tcount += 2LL * mp.k;
        // Remove all x's covered by this operation
        if (mp.d == 'U') {
            int j = mp.p; int k = mp.k;
            for (int r = 0; r < k; ++r) if (isX[r][j]) { remainMinSum -= minPlan[r][j].k; isX[r][j] = 0; }
        } else if (mp.d == 'D') {
            int j = mp.p; int k = mp.k;
            for (int r = N-k; r < N; ++r) if (isX[r][j]) { remainMinSum -= minPlan[r][j].k; isX[r][j] = 0; }
        } else if (mp.d == 'L') {
            int i = mp.p; int k = mp.k;
            for (int c = 0; c < k; ++c) if (isX[i][c]) { remainMinSum -= minPlan[i][c].k; isX[i][c] = 0; }
        } else if (mp.d == 'R') {
            int i = mp.p; int k = mp.k;
            for (int c = N-k; c < N; ++c) if (isX[i][c]) { remainMinSum -= minPlan[i][c].k; isX[i][c] = 0; }
        }
        // Safety: if Tcount might exceed limit (shouldn't), break
        if (Tcount > 4LL * N * N) break;
    }

    // Output actual sequence: for each pair (d, p, k), print k times d p, then k times opposite
    auto opposite = [](char d)->char{
        if (d == 'U') return 'D';
        if (d == 'D') return 'U';
        if (d == 'L') return 'R';
        return 'L';
    };
    vector<pair<char,int>> ops;
    ops.reserve(Tcount);
    for (auto &po : chosenPairs) {
        for (int t = 0; t < po.k; ++t) ops.emplace_back(po.d, po.p);
        char od = opposite(po.d);
        for (int t = 0; t < po.k; ++t) ops.emplace_back(od, po.p);
    }
    // Trim if somehow exceeded (shouldn't happen)
    if ((int)ops.size() > 4 * N * N) ops.resize(4 * N * N);

    for (auto &op : ops) {
        cout << op.first << " " << op.second << '\n';
    }
    return 0;
}