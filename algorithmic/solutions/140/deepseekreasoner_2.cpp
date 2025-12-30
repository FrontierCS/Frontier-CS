#include <bits/stdc++.h>
using namespace std;

typedef bitset<80> Mask;

struct Candidate {
    Mask mask;
    int x, y;
};

int main() {
    int b, k, w;
    cin >> b >> k >> w;
    int R = b;
    int N = 4 * k; // number of distances in first wave

    // Wave 1: four probes at (±R,0) and (0,±R)
    cout << "? 4 " << R << " 0 " << -R << " 0 0 " << R << " 0 " << -R << endl;
    vector<int> dist(N);
    for (int i = 0; i < N; ++i) cin >> dist[i];

    // map value -> list of indices
    map<int, vector<int>> val2idx;
    for (int i = 0; i < N; ++i) val2idx[dist[i]].push_back(i);

    vector<Candidate> candidates;
    set<Mask> candSet;

    // Generate candidate quadruples from pairs
    for (int i = 0; i < N; ++i) {
        for (int j = i + 1; j < N; ++j) {
            int d1 = dist[i], d2 = dist[j];

            // ---- Type H: (d1,d2) as (a, b) from horizontal probes ----
            if ((d2 - d1) % 2 == 0) {
                int x = (d2 - d1) / 2;
                if (abs(x) <= b) {
                    int sum = d1 + d2 - 2 * R;
                    if (sum >= 0 && sum % 2 == 0) {
                        int abs_y = sum / 2;
                        if (abs_y <= b) {
                            for (int sign_y : {1, -1}) {
                                int y = sign_y * abs_y;
                                int c_calc = abs(x) + R - y;
                                int d_calc = abs(x) + R + y;
                                auto it_c = val2idx.find(c_calc);
                                auto it_d = val2idx.find(d_calc);
                                if (it_c != val2idx.end() && it_d != val2idx.end()) {
                                    for (int i_c : it_c->second) {
                                        if (i_c == i || i_c == j) continue;
                                        for (int i_d : it_d->second) {
                                            if (i_d == i || i_d == j || i_d == i_c) continue;
                                            Mask m;
                                            m.set(i); m.set(j); m.set(i_c); m.set(i_d);
                                            if (candSet.count(m)) continue;
                                            candSet.insert(m);
                                            candidates.push_back({m, x, y});
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // ---- Type V: (d1,d2) as (c, d) from vertical probes ----
            if ((d2 - d1) % 2 == 0) {
                int y = (d2 - d1) / 2;
                if (abs(y) <= b) {
                    int sum2 = d1 + d2 - 2 * R;
                    if (sum2 >= 0 && sum2 % 2 == 0) {
                        int abs_x = sum2 / 2;
                        if (abs_x <= b) {
                            for (int sign_x : {1, -1}) {
                                int x = sign_x * abs_x;
                                int a_calc = R - x + abs(y);
                                int b_calc = R + x + abs(y);
                                auto it_a = val2idx.find(a_calc);
                                auto it_b = val2idx.find(b_calc);
                                if (it_a != val2idx.end() && it_b != val2idx.end()) {
                                    for (int i_a : it_a->second) {
                                        if (i_a == i || i_a == j) continue;
                                        for (int i_b : it_b->second) {
                                            if (i_b == i || i_b == j || i_b == i_a) continue;
                                            Mask m;
                                            m.set(i); m.set(j); m.set(i_a); m.set(i_b);
                                            if (candSet.count(m)) continue;
                                            candSet.insert(m);
                                            candidates.push_back({m, x, y});
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // Build cover lists for exact cover
    vector<vector<int>> cover(N); // for each index, list of candidate indices that contain it
    for (int idx = 0; idx < (int)candidates.size(); ++idx) {
        const Mask& m = candidates[idx].mask;
        for (int i = 0; i < N; ++i) if (m[i]) cover[i].push_back(idx);
    }

    // Backtracking to find all exact covers
    vector<vector<pair<int,int>>> rawSolutions;
    const int MAX_SOLUTIONS = 1000;
    Mask covered;
    vector<int> curSel;
    vector<pair<int,int>> curPoints;

    function<void()> dfs = [&]() {
        if ((int)rawSolutions.size() >= MAX_SOLUTIONS) return;
        if (covered.count() == N) {
            rawSolutions.push_back(curPoints);
            return;
        }
        // choose an uncovered index with fewest candidates
        int best = -1, bestCnt = 1e9;
        for (int i = 0; i < N; ++i) {
            if (!covered[i]) {
                int cnt = 0;
                for (int cid : cover[i]) {
                    const Mask& m = candidates[cid].mask;
                    if ((covered & m).none()) ++cnt;
                }
                if (cnt == 0) return; // dead end
                if (cnt < bestCnt) {
                    bestCnt = cnt;
                    best = i;
                    if (cnt == 1) break;
                }
            }
        }
        if (best == -1) return;
        // try all candidates covering best
        for (int cid : cover[best]) {
            const Candidate& cand = candidates[cid];
            if ((covered & cand.mask).any()) continue;
            covered |= cand.mask;
            curSel.push_back(cid);
            curPoints.emplace_back(cand.x, cand.y);
            dfs();
            curPoints.pop_back();
            curSel.pop_back();
            covered ^= cand.mask; // since we used |= earlier, we need to unset exactly those bits
            if ((int)rawSolutions.size() >= MAX_SOLUTIONS) return;
        }
    };

    dfs();

    // Deduplicate solutions by sorting points
    map<vector<pair<int,int>>, int> uniqMap;
    for (auto& sol : rawSolutions) {
        sort(sol.begin(), sol.end());
        uniqMap[sol] = 1;
    }
    vector<vector<pair<int,int>>> solutions;
    for (auto& p : uniqMap) solutions.push_back(p.first);

    // If only one solution, output immediately
    if (solutions.size() == 1) {
        const auto& pts = solutions[0];
        cout << "!";
        for (auto [x, y] : pts) cout << " " << x << " " << y;
        cout << endl;
        return 0;
    }

    // Multiple solutions: need verification waves
    // Predefined set of probe points (within bounds)
    vector<pair<int,int>> probes;
    probes.emplace_back(b, b);
    probes.emplace_back(b, -b);
    probes.emplace_back(-b, b);
    probes.emplace_back(-b, -b);
    // Add some grid points
    for (int i = 0; i <= 10; ++i) {
        int x = -b + (2 * b * i) / 10;
        for (int j = 0; j <= 10; ++j) {
            int y = -b + (2 * b * j) / 10;
            probes.emplace_back(x, y);
        }
    }

    vector<vector<pair<int,int>>> remaining = solutions;
    int waveUsed = 1; // already used first wave

    for (int wave = 2; wave <= w && remaining.size() > 1; ++wave) {
        int idx = wave - 2;
        if (idx >= (int)probes.size()) idx %= probes.size();
        auto [qx, qy] = probes[idx];
        cout << "? 1 " << qx << " " << qy << endl;
        vector<int> resp(k);
        for (int i = 0; i < k; ++i) cin >> resp[i];
        sort(resp.begin(), resp.end());

        vector<vector<pair<int,int>>> nextRemaining;
        for (const auto& sol : remaining) {
            vector<int> calc;
            for (auto [x, y] : sol) calc.push_back(abs(x - qx) + abs(y - qy));
            sort(calc.begin(), calc.end());
            if (calc == resp) nextRemaining.push_back(sol);
        }
        remaining = nextRemaining;
        ++waveUsed;
    }

    // Output the first remaining solution (should be unique)
    const auto& pts = remaining[0];
    cout << "!";
    for (auto [x, y] : pts) cout << " " << x << " " << y;
    cout << endl;

    return 0;
}