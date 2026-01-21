#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    mt19937 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    int t;
    if (!(cin >> t)) return 0;

    for (int tc = 0; tc < t; ++tc) {
        int n, m, start, base_move_count;
        if (!(cin >> n >> m >> start >> base_move_count)) return 0;
        for (int i = 0; i < m; ++i) {
            int u, v;
            cin >> u >> v;
        }

        unordered_map<string, unordered_map<int, int>> usageCounts;
        usageCounts.reserve(1024);

        while (true) {
            string tok;
            if (!(cin >> tok)) return 0;
            if (tok == "AC" || tok == "F") {
                break;
            }

            int d = stoi(tok);
            vector<int> degs(d), flags(d);
            for (int i = 0; i < d; ++i) {
                int di, fi;
                cin >> di >> fi;
                degs[i] = di;
                flags[i] = fi;
            }

            // Build fingerprint: d | sorted degrees
            vector<int> sortedDegs = degs;
            sort(sortedDegs.begin(), sortedDegs.end());
            string fp;
            fp.reserve(4 * d + 10);
            fp.append(to_string(d));
            fp.push_back('|');
            for (int i = 0; i < d; ++i) {
                if (i) fp.push_back(',');
                fp.append(to_string(sortedDegs[i]));
            }

            // Frequency of degrees among neighbors
            unordered_map<int, int> freq;
            freq.reserve(d * 2 + 1);
            for (int i = 0; i < d; ++i) freq[degs[i]]++;

            auto pick_best = [&](const vector<int>& cands)->int {
                vector<int> uniques;
                uniques.reserve(cands.size());
                for (int idx : cands) {
                    if (freq[degs[idx]] == 1) uniques.push_back(idx);
                }
                const vector<int>& pool = uniques.empty() ? cands : uniques;

                int bestIdx = pool[0];
                int bestDeg = degs[bestIdx];
                int bestUsage = usageCounts[fp][bestDeg];
                // Prefer higher degree, then less used, tie-break random
                for (size_t k = 1; k < pool.size(); ++k) {
                    int idx = pool[k];
                    int dg = degs[idx];
                    int us = usageCounts[fp][dg];
                    if (dg > bestDeg) {
                        bestDeg = dg; bestUsage = us; bestIdx = idx;
                    } else if (dg == bestDeg) {
                        if (us < bestUsage) {
                            bestUsage = us; bestIdx = idx;
                        } else if (us == bestUsage) {
                            if (uniform_int_distribution<int>(0, 1)(rng) == 0) {
                                bestIdx = idx;
                            }
                        }
                    }
                }
                return bestIdx;
            };

            vector<int> cand0;
            cand0.reserve(d);
            for (int i = 0; i < d; ++i) if (flags[i] == 0) cand0.push_back(i);

            int chosenIdx;
            if (!cand0.empty()) {
                chosenIdx = pick_best(cand0);
            } else {
                vector<int> all(d);
                iota(all.begin(), all.end(), 0);
                chosenIdx = pick_best(all);
            }

            // Update usage counts for fingerprint/degree
            usageCounts[fp][degs[chosenIdx]]++;

            cout << (chosenIdx + 1) << endl;
            cout.flush();
        }
    }

    return 0;
}