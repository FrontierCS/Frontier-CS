#include <bits/stdc++.h>
using namespace std;

struct Candidate {
    char dir;
    int p;
    int k; // number of shifts in chosen direction
    unsigned long long mask; // which oni are removed
    int cost() const { return 2 * k; } // total operations
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    if (!(cin >> N)) return 0;
    vector<string> C(N);
    for (int i = 0; i < N; ++i) cin >> C[i];

    // Collect Oni and Fuku positions
    vector<pair<int,int>> oni; // (i, j)
    vector<vector<bool>> isF(N, vector<bool>(N, false));
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (C[i][j] == 'x') oni.emplace_back(i, j);
            else if (C[i][j] == 'o') isF[i][j] = true;
        }
    }
    int M = (int)oni.size(); // should be 2N

    auto noFUp = [&](int i, int j)->bool{
        for (int r = 0; r < i; ++r) if (isF[r][j]) return false;
        return true;
    };
    auto noFDown = [&](int i, int j)->bool{
        for (int r = i + 1; r < N; ++r) if (isF[r][j]) return false;
        return true;
    };
    auto noFLeft = [&](int i, int j)->bool{
        for (int c = 0; c < j; ++c) if (isF[i][c]) return false;
        return true;
    };
    auto noFRight = [&](int i, int j)->bool{
        for (int c = j + 1; c < N; ++c) if (isF[i][c]) return false;
        return true;
    };

    auto append_ops = [&](vector<pair<char,int>>& ops, char d, int p, int k){
        char opp;
        if (d == 'U') opp = 'D';
        else if (d == 'D') opp = 'U';
        else if (d == 'L') opp = 'R';
        else opp = 'L';
        for (int t = 0; t < k; ++t) ops.emplace_back(d, p);
        for (int t = 0; t < k; ++t) ops.emplace_back(opp, p);
    };

    // Baseline: per-oni minimal allowed direction
    vector<pair<char,int>> base_ops;
    for (int idx = 0; idx < M; ++idx) {
        int i = oni[idx].first;
        int j = oni[idx].second;
        int bestK = INT_MAX;
        char bestD = 'U';
        int bestP = j;

        if (noFUp(i,j)) {
            int k = i + 1;
            if (k < bestK) { bestK = k; bestD = 'U'; bestP = j; }
        }
        if (noFDown(i,j)) {
            int k = N - i;
            if (k < bestK) { bestK = k; bestD = 'D'; bestP = j; }
        }
        if (noFLeft(i,j)) {
            int k = j + 1;
            if (k < bestK) { bestK = k; bestD = 'L'; bestP = i; }
        }
        if (noFRight(i,j)) {
            int k = N - j;
            if (k < bestK) { bestK = k; bestD = 'R'; bestP = i; }
        }
        append_ops(base_ops, bestD, bestP, bestK);
    }

    // Greedy covering with candidate operations (per-oni per-allowed-direction)
    vector<Candidate> cands;
    cands.reserve(M * 4);
    auto key_encode = [](char d, int p, int k)->uint32_t{
        uint32_t di = (d=='U'?0u:(d=='D'?1u:(d=='L'?2u:3u)));
        return (di<<16) | ((uint32_t)p<<8) | (uint32_t)k;
    };
    unordered_map<uint32_t, int> dedup; // key -> index in cands

    for (int idx = 0; idx < M; ++idx) {
        int i = oni[idx].first;
        int j = oni[idx].second;

        // Helper to add candidate
        auto add_cand = [&](char d, int p, int k){
            uint32_t key = key_encode(d, p, k);
            if (dedup.count(key)) return;
            Candidate cand; cand.dir = d; cand.p = p; cand.k = k; cand.mask = 0ULL;
            if (d == 'U') {
                for (int t = 0; t < M; ++t) {
                    if (oni[t].second == p && oni[t].first <= i) cand.mask |= (1ULL << t);
                }
            } else if (d == 'D') {
                for (int t = 0; t < M; ++t) {
                    if (oni[t].second == p && oni[t].first >= i) cand.mask |= (1ULL << t);
                }
            } else if (d == 'L') {
                for (int t = 0; t < M; ++t) {
                    if (oni[t].first == p && oni[t].second <= j) cand.mask |= (1ULL << t);
                }
            } else { // 'R'
                for (int t = 0; t < M; ++t) {
                    if (oni[t].first == p && oni[t].second >= j) cand.mask |= (1ULL << t);
                }
            }
            dedup[key] = (int)cands.size();
            cands.push_back(cand);
        };

        if (noFUp(i,j)) add_cand('U', j, i+1);
        if (noFDown(i,j)) add_cand('D', j, N - i);
        if (noFLeft(i,j)) add_cand('L', i, j+1);
        if (noFRight(i,j)) add_cand('R', i, N - j);
    }

    unsigned long long leftover = (M == 64 ? ~0ULL : ((1ULL<<M) - 1));
    vector<pair<char,int>> greedy_ops;
    int greedy_cost = 0;
    while (leftover) {
        int best = -1;
        double best_ratio = -1.0;
        int best_new = -1;
        int best_cost = INT_MAX;
        for (int ci = 0; ci < (int)cands.size(); ++ci) {
            unsigned long long newmask = cands[ci].mask & leftover;
            if (!newmask) continue;
            int newcnt = __builtin_popcountll(newmask);
            int cost = cands[ci].cost();
            double ratio = (double)newcnt / (double)cost;
            if (ratio > best_ratio + 1e-12 ||
                (abs(ratio - best_ratio) <= 1e-12 && (newcnt > best_new ||
                   (newcnt == best_new && cost < best_cost)))) {
                best = ci;
                best_ratio = ratio;
                best_new = newcnt;
                best_cost = cost;
            }
        }
        if (best == -1) break; // should not happen
        // apply
        append_ops(greedy_ops, cands[best].dir, cands[best].p, cands[best].k);
        greedy_cost += cands[best].cost();
        leftover &= ~cands[best].mask;
    }

    // If greedy failed to cover all (shouldn't), fall back to baseline for remaining
    if (leftover) {
        for (int idx = 0; idx < M; ++idx) {
            if (!(leftover & (1ULL<<idx))) continue;
            int i = oni[idx].first, j = oni[idx].second;
            int bestK = INT_MAX; char bestD = 'U'; int bestP = j;
            if (noFUp(i,j)) { int k = i+1; if (k < bestK) { bestK = k; bestD = 'U'; bestP = j; } }
            if (noFDown(i,j)) { int k = N-i; if (k < bestK) { bestK = k; bestD = 'D'; bestP = j; } }
            if (noFLeft(i,j)) { int k = j+1; if (k < bestK) { bestK = k; bestD = 'L'; bestP = i; } }
            if (noFRight(i,j)) { int k = N-j; if (k < bestK) { bestK = k; bestD = 'R'; bestP = i; } }
            append_ops(greedy_ops, bestD, bestP, bestK);
            greedy_cost += 2 * bestK;
        }
    }

    // Choose better between greedy and baseline (by operation count)
    vector<pair<char,int>> &ans = (greedy_ops.size() <= base_ops.size() ? greedy_ops : base_ops);

    // Ensure limit
    int limit = 4 * N * N;
    if ((int)ans.size() > limit) {
        // Fallback to baseline if greedy exceeds, else if still exceeds, trim (shouldn't happen)
        ans = base_ops;
        if ((int)ans.size() > limit) {
            // In an extreme improbable case, truncate to limit to avoid WA (though correctness may degrade)
            ans.resize(limit);
        }
    }

    // Output operations
    for (auto &op : ans) {
        cout << op.first << ' ' << op.second << '\n';
    }
    return 0;
}