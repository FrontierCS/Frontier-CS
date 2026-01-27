#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());

    int t;
    if (!(cin >> t)) return 0;
    for (int tc = 0; tc < t; ++tc) {
        int n, m, start, base_move_count;
        if (!(cin >> n >> m >> start >> base_move_count)) return 0;

        vector<vector<int>> adj(n + 1);
        vector<int> deg(n + 1, 0);
        for (int i = 0; i < m; ++i) {
            int u, v;
            cin >> u >> v;
            adj[u].push_back(v);
            adj[v].push_back(u);
            deg[u]++; deg[v]++;
        }

        // Precompute signature for each vertex: sorted list of neighbor degrees
        vector<string> vSig(n + 1);
        unordered_map<string, int> sigId;
        vector<vector<long long>> useCounts; // per signature ID, usage count per degree (0..n)

        auto makeSig = [&](const vector<int>& dlist) {
            vector<int> srt = dlist;
            sort(srt.begin(), srt.end());
            string s;
            s.reserve(srt.size() * 3 + 2);
            for (int x : srt) {
                s.push_back(',');
                s += to_string(x);
            }
            return s;
        };

        // Build signature IDs from the graph description
        for (int v = 1; v <= n; ++v) {
            vector<int> nd;
            nd.reserve(adj[v].size());
            for (int u : adj[v]) nd.push_back(deg[u]);
            string s = makeSig(nd);
            vSig[v] = s;
            if (!sigId.count(s)) {
                int id = (int)sigId.size();
                sigId[s] = id;
            }
        }
        // Initialize useCounts for each signature
        useCounts.assign(sigId.size(), vector<long long>(n + 1, 0));

        long long step = 0;
        int last_d = -1; // degree of previous vertex
        bool last_move_to_unvisited = false;

        while (true) {
            string tok;
            if (!(cin >> tok)) return 0;
            if (tok == "AC" || tok == "F") {
                // Finish this test case and proceed
                break;
            }
            int d = stoi(tok);
            vector<int> neighDeg(d), neighFlag(d);
            for (int i = 0; i < d; ++i) {
                int dg, fl;
                cin >> dg >> fl;
                neighDeg[i] = dg;
                neighFlag[i] = fl;
            }

            // Compute current signature string
            string curSig = makeSig(neighDeg);
            int curSigId;
            auto it = sigId.find(curSig);
            if (it == sigId.end()) {
                // Unknown signature (shouldn't happen if graph description matches interaction), add it
                curSigId = (int)sigId.size();
                sigId[curSig] = curSigId;
                useCounts.push_back(vector<long long>(n + 1, 0));
            } else {
                curSigId = it->second;
            }

            // Determine candidate set: unvisited neighbors if any, else all
            vector<int> candidates;
            for (int i = 0; i < d; ++i) if (neighFlag[i] == 0) candidates.push_back(i);
            bool had_unvisited = !candidates.empty();
            if (candidates.empty()) {
                for (int i = 0; i < d; ++i) candidates.push_back(i);
            }

            int chosen = -1;

            // If no unvisited neighbors and last step went to an unvisited neighbor,
            // try to backtrack to the parent using previous degree if uniquely identifiable.
            if (!had_unvisited && last_move_to_unvisited && last_d >= 0) {
                int count_parent_candidates = 0;
                int parent_idx = -1;
                for (int i = 0; i < d; ++i) {
                    if (neighFlag[i] == 1 && neighDeg[i] == last_d) {
                        count_parent_candidates++;
                        parent_idx = i;
                        if (count_parent_candidates > 1) break;
                    }
                }
                if (count_parent_candidates == 1) {
                    chosen = parent_idx;
                }
            }

            if (chosen == -1) {
                // Heuristic selection among candidates
                vector<int> freq(n + 1, 0);
                for (int idx : candidates) {
                    int gd = neighDeg[idx];
                    if (gd >= 0 && gd <= n) freq[gd]++;
                }

                // Select index with:
                // 1) minimal useCounts for degree in this signature (to diversify),
                // 2) prefer degrees that are unique in candidates,
                // 3) prefer larger degree,
                // 4) random tie-break
                long long best_uc = LLONG_MAX;
                int best_unique = 2; // 0 if unique, 1 otherwise
                int best_deg = -1;
                vector<int> best_indices;

                for (int idx : candidates) {
                    int gd = neighDeg[idx];
                    long long uc = (gd >= 0 && gd <= n) ? useCounts[curSigId][gd] : 0;
                    int uniq = (gd >= 0 && gd <= n && freq[gd] == 1) ? 0 : 1;
                    // compare (uc, uniq, -gd)
                    bool better = false;
                    if (uc < best_uc) better = true;
                    else if (uc == best_uc) {
                        if (uniq < best_unique) better = true;
                        else if (uniq == best_unique) {
                            if (gd > best_deg) better = true;
                        }
                    }
                    if (better) {
                        best_uc = uc;
                        best_unique = uniq;
                        best_deg = gd;
                        best_indices.clear();
                        best_indices.push_back(idx);
                    } else if (uc == best_uc && uniq == best_unique && gd == best_deg) {
                        best_indices.push_back(idx);
                    }
                }

                if (!best_indices.empty()) {
                    uniform_int_distribution<int> dist(0, (int)best_indices.size() - 1);
                    chosen = best_indices[dist(rng)];
                } else {
                    // Fallback random choice (shouldn't happen)
                    uniform_int_distribution<int> dist(0, d - 1);
                    chosen = dist(rng);
                }
            }

            int out = chosen + 1;
            cout << out << '\n' << flush;

            // Update usage counts and move metadata
            int chosen_deg = neighDeg[chosen];
            if (chosen_deg >= 0 && chosen_deg <= n) {
                useCounts[curSigId][chosen_deg]++;
            }
            bool moved_to_unvisited = (neighFlag[chosen] == 0);
            last_move_to_unvisited = moved_to_unvisited;
            last_d = d;
            step++;
        }
    }

    return 0;
}