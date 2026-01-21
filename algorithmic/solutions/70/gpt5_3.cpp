#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count() ^ (uint64_t)(uintptr_t)new int);

    auto pick_random = [&](const vector<int>& v)->int{
        if (v.empty()) return -1;
        uint64_t x = rng();
        return v[(size_t)(x % v.size())];
    };

    int t;
    if (!(cin >> t)) return 0;
    for (int tc = 0; tc < t; ++tc) {
        int n, m, start, base_move_count;
        if (!(cin >> n >> m >> start >> base_move_count)) return 0;
        for (int i = 0; i < m; ++i) {
            int u, v;
            cin >> u >> v;
        }

        int prev_d1 = -1; // degree of previous vertex
        int prev_d2 = -1; // degree two steps back

        while (true) {
            string tok;
            if (!(cin >> tok)) {
                return 0;
            }
            if (tok == "AC" || tok == "F") {
                // Test ends
                break;
            }
            // tok should be degree d
            int d = stoi(tok);
            vector<int> deg(d), flagv(d);
            for (int i = 0; i < d; ++i) {
                int di, fi;
                cin >> di >> fi;
                deg[i] = di;
                flagv[i] = fi;
            }

            int moveIdx = 0; // 1-based
            vector<int> unvisited, visited;
            for (int i = 0; i < d; ++i) {
                if (flagv[i] == 0) unvisited.push_back(i);
                else visited.push_back(i);
            }

            if (!unvisited.empty()) {
                // Prefer unvisited neighbor with maximum degree (tie-break randomly)
                int bestDeg = -1;
                vector<int> cand;
                for (int idx : unvisited) {
                    if (deg[idx] > bestDeg) {
                        bestDeg = deg[idx];
                        cand.clear();
                        cand.push_back(idx);
                    } else if (deg[idx] == bestDeg) {
                        cand.push_back(idx);
                    }
                }
                int pick = pick_random(cand);
                if (pick == -1) pick = unvisited[0];
                moveIdx = pick + 1;
            } else {
                // No unvisited neighbors: attempt to backtrack using degree hints
                vector<int> cand;
                if (prev_d1 != -1) {
                    for (int idx : visited) if (deg[idx] == prev_d1) cand.push_back(idx);
                }
                if (cand.empty() && prev_d2 != -1) {
                    for (int idx : visited) if (deg[idx] == prev_d2) cand.push_back(idx);
                }
                if (cand.empty()) {
                    // Pick visited neighbor with degree closest to prev_d1, else random
                    if (!visited.empty()) {
                        int bestIdx = visited[0];
                        int bestScore = INT_MAX;
                        for (int idx : visited) {
                            int diff = (prev_d1 == -1 ? 0 : abs(deg[idx] - prev_d1));
                            if (diff < bestScore) {
                                bestScore = diff;
                                bestIdx = idx;
                            } else if (diff == bestScore) {
                                // tie-break randomly
                                if ((rng() & 1) == 0) bestIdx = idx;
                            }
                        }
                        moveIdx = bestIdx + 1;
                    } else {
                        // Should not happen, but fallback
                        moveIdx = 1;
                    }
                } else {
                    int pick = pick_random(cand);
                    if (pick == -1) pick = visited[0];
                    moveIdx = pick + 1;
                }
            }

            cout << moveIdx << '\n' << flush;

            // Update previous degrees
            prev_d2 = prev_d1;
            prev_d1 = d;
        }
    }
    return 0;
}