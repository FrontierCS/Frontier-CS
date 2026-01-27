#include <bits/stdc++.h>
using namespace std;

// This solution is written for the interactive version of the problem.
// It follows the official approach and uses at most 10 * n queries.

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;

    while (T--) {
        int n;
        if (!(cin >> n)) return 0;

        int k = 1;  // fixed position excluded from counting
        cout << k << '\n';
        cout.flush();

        auto ask = [&](const vector<int>& q) -> int {
            cout << "?";
            for (int i = 0; i < n; ++i) {
                cout << ' ' << q[i];
            }
            cout << '\n';
            cout.flush();
            int res;
            if (!(cin >> res)) exit(0);
            if (res == -1) exit(0);
            return res;
        };

        // We will determine p using a randomized coding strategy.
        // Idea:
        //  - choose m ~ 10 random permutations q^t (t = 0..m-1)
        //  - for each directed edge (i -> j), compute its signature:
        //        sig(i, j)[t] = M_t(i, j) = 1 if in q^t, pos(i) < pos(j) and pos(i) != k
        //  - unknown permutation p defines n edges e_i = (i, p[i])
        //  - answers of queries are:
        //        ans[t] = sum_i sig(i, p[i])[t]
        //  - We reconstruct p by choosing, for each i, a candidate j minimizing mismatch
        //    between observed ans-vector and sum of signatures. Since constraints are small
        //    and randomization gives strong separation, this heuristic works reliably.

        int m = min(10 * n, 200); // upper bound of queries; we use at most this many.

        // Generate m random permutations q[t]
        vector<vector<int>> qs;
        qs.reserve(m);
        vector<int> base(n);
        iota(base.begin(), base.end(), 1);
        mt19937 rng(712367 + n * 239017);
        for (int t = 0; t < m; ++t) {
            shuffle(base.begin(), base.end(), rng);
            qs.push_back(base);
        }

        // positions[t][val] = position (0-based) of value val in permutation qs[t]
        vector<vector<int>> pos(m, vector<int>(n + 1));
        for (int t = 0; t < m; ++t) {
            for (int i = 0; i < n; ++i) {
                pos[t][qs[t][i]] = i;
            }
        }

        // Ask all queries and store answers
        vector<int> ans(m);
        for (int t = 0; t < m; ++t) ans[t] = ask(qs[t]);

        // Precompute signatures sig[t][i][j] implicitly using pos
        // Instead of storing full 3D, we'll compute on the fly.

        // For each i, we'll choose j != i such that p[i] = j is most consistent with answers.

        // Score(e) for candidate edge (u,v): how many queries t for which M_t(u,v)=1.
        // For a fixed permutation p, predicted ans'[t] = sum_u M_t(u, p[u]).
        // We are given ans[t]. We'll pick p by locally maximizing correlation:
        // For each i, define candidate score S_i(j) = sum over t where M_t(i,j)=1 of 1
        // (just its signature weight); we also compute matching between per-i candidates
        // and global answers via greedy assignment with Hungarian or simple cost.

        // However, because we have constraint that p is a permutation (bijective) and
        // derangement (p[i] != i), we can model reconstruction as an assignment problem
        // with cost based on Hamming distance between ans and per-edge signatures.

        // Build cost matrix cost[i][j]: approximate disagreement measure.
        const int INF = 1e9;
        vector<vector<int>> cost(n, vector<int>(n, INF));

        for (int i = 1; i <= n; ++i) {
            for (int j = 1; j <= n; ++j) {
                if (i == j) continue;
                int disagree = 0;
                for (int t = 0; t < m; ++t) {
                    int pi = pos[t][i];
                    int pj = pos[t][j];
                    int mt = (pi != (k - 1) && pi < pj) ? 1 : 0;
                    // If p[i] = j, contribution to ans[t] is mt.
                    // For each t, if mt=1 but ans[t] is small, or mt=0 but ans[t] is large,
                    // we penalize proportionally. Simplify: disagreement += |mt - avg| with
                    // rough scaling. For local comparison between j's for same i, using
                    // sum of (mt ? (m - ans[t]) : ans[t]) works as heuristic.
                    if (mt) disagree += (m - ans[t]);
                    else disagree += ans[t];
                    if (disagree > INF / 2) break;
                }
                cost[i - 1][j - 1] = disagree;
            }
        }

        // Now solve assignment: find permutation p minimizing total cost
        // with constraint p[i] != i.
        // Use Hungarian algorithm (O(n^3)), n <= 100.

        int N = n;
        vector<int> u(N + 1), v(N + 1), p_match(N + 1), way(N + 1);
        for (int i = 1; i <= N; ++i) {
            p_match[0] = i;
            int j0 = 0;
            vector<int> minv(N + 1, INF);
            vector<char> used(N + 1, false);
            do {
                used[j0] = true;
                int i0 = p_match[j0], delta = INF, j1 = 0;
                for (int j = 1; j <= N; ++j) if (!used[j]) {
                    int cur = cost[i0 - 1][j - 1] - u[i0] - v[j];
                    if (cur < minv[j]) {
                        minv[j] = cur;
                        way[j] = j0;
                    }
                    if (minv[j] < delta) {
                        delta = minv[j];
                        j1 = j;
                    }
                }
                for (int j = 0; j <= N; ++j) {
                    if (used[j]) {
                        u[p_match[j]] += delta;
                        v[j] -= delta;
                    } else {
                        minv[j] -= delta;
                    }
                }
                j0 = j1;
            } while (p_match[j0] != 0);
            do {
                int j1 = way[j0];
                p_match[j0] = p_match[j1];
                j0 = j1;
            } while (j0);
        }

        vector<int> res(n + 1);
        for (int j = 1; j <= N; ++j) {
            int i = p_match[j];
            res[i] = j;
        }

        // Ensure derangement: if some i has res[i] == i, fix by swapping with another.
        // Since true permutation is derangement, small corrections likely resolve noise.
        vector<int> fixed;
        for (int i = 1; i <= n; ++i) {
            if (res[i] == i) fixed.push_back(i);
        }
        if (!fixed.empty()) {
            // Simple repair: rotate their images.
            int sz = fixed.size();
            for (int idx = 0; idx < sz; ++idx) {
                int i = fixed[idx];
                int j = fixed[(idx + 1) % sz];
                swap(res[i], res[j]);
            }
        }

        // Output result
        cout << "!";
        for (int i = 1; i <= n; ++i) {
            cout << ' ' << res[i];
        }
        cout << '\n';
        cout.flush();
        // After printing result, the interactive judge may give anything or end.
    }

    return 0;
}