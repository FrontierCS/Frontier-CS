#include <iostream>
#include <vector>
#include <algorithm>
#include <climits>

using namespace std;

const int dx[8] = {-2, -2, -1, -1, 1, 1, 2, 2};
const int dy[8] = {-1, 1, -2, 2, -2, 2, -1, 1};

int n;

inline bool inside(int r, int c) {
    return r >= 1 && r <= n && c >= 1 && c <= n;
}

int border_dist(int r, int c) {
    return min(min(r-1, n-r), min(c-1, n-c));
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n;
    int sr, sc;
    cin >> sr >> sc;

    vector<vector<bool>> visited(n+1, vector<bool>(n+1, false));
    vector<pair<int, int>> path;
    path.reserve(n * n);

    int r = sr, c = sc;
    visited[r][c] = true;
    path.emplace_back(r, c);

    while (true) {
        vector<pair<int, int>> candidates;
        for (int d = 0; d < 8; ++d) {
            int nr = r + dx[d];
            int nc = c + dy[d];
            if (inside(nr, nc) && !visited[nr][nc]) {
                candidates.emplace_back(nr, nc);
            }
        }

        if (candidates.empty()) break;

        // Compute degree for each candidate
        vector<int> degrees;
        degrees.reserve(candidates.size());
        for (auto [nr, nc] : candidates) {
            int deg = 0;
            for (int d = 0; d < 8; ++d) {
                int tr = nr + dx[d];
                int tc = nc + dy[d];
                if (inside(tr, tc) && !visited[tr][tc]) {
                    ++deg;
                }
            }
            degrees.push_back(deg);
        }

        // Find candidate with minimal degree
        int min_deg = INT_MAX;
        for (int deg : degrees) {
            if (deg < min_deg) min_deg = deg;
        }

        // Filter candidates with minimal degree
        vector<pair<int, int>> filtered;
        for (size_t i = 0; i < candidates.size(); ++i) {
            if (degrees[i] == min_deg) {
                filtered.push_back(candidates[i]);
            }
        }

        // Tie-breaking: choose the one with smallest border distance
        pair<int, int> best = filtered[0];
        int best_border = border_dist(best.first, best.second);
        for (size_t i = 1; i < filtered.size(); ++i) {
            int bd = border_dist(filtered[i].first, filtered[i].second);
            if (bd < best_border) {
                best_border = bd;
                best = filtered[i];
            } else if (bd == best_border) {
                // Further tie-breaking: by row then column
                if (filtered[i].first < best.first) {
                    best = filtered[i];
                } else if (filtered[i].first == best.first && filtered[i].second < best.second) {
                    best = filtered[i];
                }
            }
        }

        r = best.first;
        c = best.second;
        visited[r][c] = true;
        path.emplace_back(r, c);
    }

    cout << path.size() << "\n";
    for (auto [pr, pc] : path) {
        cout << pr << " " << pc << "\n";
    }
    return 0;
}