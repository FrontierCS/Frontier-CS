#include <iostream>
#include <vector>
#include <string>
#include <cstdlib>
#include <algorithm>
#include <climits>

using namespace std;

struct Cell {
    int i, j, amt;
};

int manhattan(int i1, int j1, int i2, int j2) {
    return abs(i1 - i2) + abs(j1 - j2);
}

void move_to(int& ci, int& cj, int ni, int nj, vector<string>& ans) {
    while (ci < ni) { ans.push_back("D"); ci++; }
    while (ci > ni) { ans.push_back("U"); ci--; }
    while (cj < nj) { ans.push_back("R"); cj++; }
    while (cj > nj) { ans.push_back("L"); cj--; }
}

int main() {
    int N;
    cin >> N;
    vector<vector<int>> h(N, vector<int>(N));
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            cin >> h[i][j];
        }
    }

    vector<Cell> sources, sinks;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (h[i][j] > 0) {
                sources.push_back({i, j, h[i][j]});
            } else if (h[i][j] < 0) {
                sinks.push_back({i, j, -h[i][j]});
            }
        }
    }

    int ci = 0, cj = 0;
    int load = 0;
    vector<string> ans;

    while (!sources.empty() || !sinks.empty()) {
        long long best_score = 1e18;
        int best_type = -1; // 0: source, 1: sink
        int best_idx = -1;

        // Evaluate sources
        for (size_t idx = 0; idx < sources.size(); ++idx) {
            int d = manhattan(ci, cj, sources[idx].i, sources[idx].j);
            long long score = (long long)d * (100 + load) + sources[idx].amt;
            if (score < best_score) {
                best_score = score;
                best_type = 0;
                best_idx = idx;
            }
        }

        // Evaluate sinks only if we have load
        if (load > 0) {
            for (size_t idx = 0; idx < sinks.size(); ++idx) {
                int d = manhattan(ci, cj, sinks[idx].i, sinks[idx].j);
                long long score = (long long)d * (100 + load) + sinks[idx].amt;
                if (score < best_score) {
                    best_score = score;
                    best_type = 1;
                    best_idx = idx;
                }
            }
        }

        // If no candidate (should not happen), break
        if (best_idx == -1) break;

        if (best_type == 0) {
            Cell s = sources[best_idx];
            move_to(ci, cj, s.i, s.j, ans);
            ans.push_back("+" + to_string(s.amt));
            load += s.amt;
            // Remove the source
            sources[best_idx] = sources.back();
            sources.pop_back();
        } else {
            Cell s = sinks[best_idx];
            move_to(ci, cj, s.i, s.j, ans);
            ans.push_back("-" + to_string(s.amt));
            load -= s.amt;
            // Remove the sink
            sinks[best_idx] = sinks.back();
            sinks.pop_back();
        }
    }

    // Output operations
    for (const string& op : ans) {
        cout << op << endl;
    }

    return 0;
}