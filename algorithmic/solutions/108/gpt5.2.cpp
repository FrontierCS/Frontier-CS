#include <bits/stdc++.h>
using namespace std;

struct RNG {
    std::mt19937 rng;
    RNG(uint64_t seed) : rng((uint32_t)seed) {}
    int nextInt(int l, int r) { // inclusive
        std::uniform_int_distribution<int> dist(l, r);
        return dist(rng);
    }
    uint32_t nextU32() { return rng(); }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;
    int N = n * m;

    int maxTotalQ = 30000;
    int reserveOrder = (n - 1) * (n - 1) + 5;
    int maxSearchQ = maxTotalQ - reserveOrder;

    vector<int> rot(n, 0);
    vector<pair<int,int>> hist;
    int queries = 0;

    uint64_t seed = 0x9e3779b97f4a7c15ULL ^ (uint64_t)n * 1000003ULL ^ (uint64_t)m * 10007ULL;
    RNG R(seed);

    auto query = [&](int x, int d) -> int {
        cout << "? " << x << " " << d << "\n";
        cout.flush();
        int a;
        if (!(cin >> a)) exit(0);
        if (a < 0) exit(0);
        queries++;
        rot[x] = (rot[x] + d) % N;
        if (rot[x] < 0) rot[x] += N;
        return a;
    };

    auto rollbackTo = [&](size_t target, int &a, int qLimit) {
        while (hist.size() > target && queries < qLimit) {
            auto [x, d] = hist.back();
            hist.pop_back();
            a = query(x, -d);
        }
    };

    auto randomMoveAccept = [&](int &a, int qLimit, bool allowUphill) {
        if (queries >= qLimit) return;
        int x = R.nextInt(0, n - 1);
        int d = (R.nextU32() & 1) ? 1 : -1;

        int a2 = query(x, d);
        int delta = a2 - a;

        bool accept = false;
        if (delta < 0) accept = true;
        else if (delta == 0) {
            // accept some equal moves to drift on plateaus
            accept = (R.nextU32() & 3) != 0; // 75%
        } else { // delta == +1 (should be, as change is at most 1)
            if (allowUphill) {
                // accept rarely; more often when a is small and we need to escape
                int denom = (a <= 30 ? 5 : (a <= 100 ? 12 : 25));
                accept = (R.nextInt(1, denom) == 1);
            }
        }

        if (accept) {
            a = a2;
            hist.push_back({x, d});
        } else {
            if (queries < qLimit) {
                a = query(x, -d);
            }
        }
    };

    // Initial query to get display value.
    int a = query(0, 1);
    hist.push_back({0, 1});

    int bestA = a;
    size_t bestIdx = hist.size();

    int noImproveQ = 0;

    auto noteIfBest = [&]() {
        if (a < bestA) {
            bestA = a;
            bestIdx = hist.size();
            noImproveQ = 0;
        }
    };

    noteIfBest();

    // Phase 1: reach a == 0 (perfect cover)
    while (a > 0 && queries < maxSearchQ) {
        int prevA = a;

        if (a <= 35) {
            // Try to deterministically find a decreasing move.
            bool improved = false;

            // Try a subset first (randomized), then full scan.
            int trials = min(3 * n, 200);
            for (int t = 0; t < trials && queries + 2 <= maxSearchQ && !improved; t++) {
                int x = R.nextInt(0, n - 1);
                int d = (R.nextU32() & 1) ? 1 : -1;
                int a2 = query(x, d);
                if (a2 < a) {
                    a = a2;
                    hist.push_back({x, d});
                    improved = true;
                } else {
                    a = query(x, -d);
                }
            }

            for (int x = 0; x < n && queries + 2 <= maxSearchQ && !improved; x++) {
                for (int d : {1, -1}) {
                    if (queries + 2 > maxSearchQ) break;
                    int a2 = query(x, d);
                    if (a2 < a) {
                        a = a2;
                        hist.push_back({x, d});
                        improved = true;
                        break;
                    } else {
                        a = query(x, -d);
                    }
                }
            }

            if (!improved) {
                // Small shake
                int steps = min(60, maxSearchQ - queries);
                for (int s = 0; s < steps && queries < maxSearchQ; s++) {
                    int x = R.nextInt(0, n - 1);
                    int d = (R.nextU32() & 1) ? 1 : -1;
                    a = query(x, d);
                    hist.push_back({x, d});
                }
            }
        } else {
            // Mostly greedy random steps; allow uphill occasionally to escape traps.
            bool allowUphill = (noImproveQ > 1500);
            randomMoveAccept(a, maxSearchQ, allowUphill);
        }

        if (a < prevA) noImproveQ = 0;
        else noImproveQ++;

        noteIfBest();

        // If we're wandering far from best, occasionally rollback to best to refocus.
        if (queries + (int)(hist.size() - bestIdx) + 50 < maxSearchQ && a > bestA + 50 && (noImproveQ > 2000)) {
            rollbackTo(bestIdx, a, maxSearchQ);
            noImproveQ = 0;
        }

        // Periodic mild shake if stuck
        if (noImproveQ > 3500 && queries + 200 < maxSearchQ) {
            int steps = 120;
            for (int s = 0; s < steps && queries < maxSearchQ; s++) {
                int x = R.nextInt(0, n - 1);
                int d = (R.nextU32() & 1) ? 1 : -1;
                a = query(x, d);
                hist.push_back({x, d});
            }
            noImproveQ = 0;
            noteIfBest();
        }
    }

    if (a != 0) {
        // Last resort: rollback to best and use remaining (including some of reserve) to try to finish.
        int hardLimit = maxTotalQ - ((n - 1) * (n - 1) + 1); // strict worst-case for order
        if (queries < hardLimit) {
            rollbackTo(bestIdx, a, hardLimit);
            while (a > 0 && queries < hardLimit) {
                // more aggressive: accept some uphill moves
                randomMoveAccept(a, hardLimit, true);
                noteIfBest();
                if (a == 0) break;
            }
        }
    }

    // Phase 2: extract order assuming a == 0.
    // We need remaining budget for worst-case order extraction.
    // If a != 0 still, we will try to proceed anyway but likely fail; interactive judge would require correctness.
    vector<int> order;
    order.reserve(n);
    vector<char> used(n, 0);
    order.push_back(0);
    used[0] = 1;

    if (a == 0) {
        // Create defect
        a = query(0, 1);

        // Expected a == 1 in perfect tiling; but be tolerant.
        // If not 1, we still attempt extraction heuristically.
        for (int step = 1; step < n; step++) {
            int found = -1;
            for (int cand = 1; cand < n; cand++) {
                if (used[cand]) continue;

                int a2 = query(cand, 1);

                bool ok = false;
                if (step == n - 1) ok = (a2 == 0); // last ring should close the defect
                else ok = (a2 == 1);

                if (ok) {
                    used[cand] = 1;
                    order.push_back(cand);
                    a = a2;
                    found = cand;
                    break;
                } else {
                    a = query(cand, -1);
                }
            }
            if (found == -1) {
                // Fallback: if something went unexpected, just mark remaining in any order.
                for (int cand = 1; cand < n; cand++) {
                    if (!used[cand]) {
                        used[cand] = 1;
                        order.push_back(cand);
                    }
                }
                break;
            }
        }
    } else {
        // Fallback if we somehow didn't reach a==0 (shouldn't happen in a correct solution).
        for (int i = 1; i < n; i++) order.push_back(i);
    }

    vector<int> pos(n, 0);
    for (int i = 0; i < (int)order.size(); i++) pos[order[i]] = i;

    cout << "!";
    for (int i = 1; i < n; i++) {
        int pi = (pos[i] * m) % N;
        cout << " " << pi;
    }
    cout << "\n";
    cout.flush();
    return 0;
}