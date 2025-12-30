#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, m;
    cin >> n >> m;
    vector<vector<int>> poles(n + 2);
    vector<vector<int>> cnt(n + 1, vector<int>(n + 2, 0));
    for (int i = 1; i <= n; i++) {
        poles[i].resize(m);
        for (int j = 0; j < m; j++) {
            cin >> poles[i][j];
            cnt[poles[i][j]][i]++;
        }
    }
    // No need to reverse; input bottom to top, vector[0] bottom, back() top

    vector<tuple<int, int, int>> candidates;
    for (int c = 1; c <= n; c++) {
        for (int p = 1; p <= n + 1; p++) {
            candidates.emplace_back(cnt[c][p], c, p);
        }
    }
    sort(candidates.rbegin(), candidates.rend());

    vector<int> target(n + 1, 0);
    vector<int> pole_color(n + 2, 0);
    for (auto& t : candidates) {
        int cn, c, p;
        tie(cn, c, p) = t;
        if (target[c] == 0 && pole_color[p] == 0) {
            target[c] = p;
            pole_color[p] = c;
        }
    }

    vector<int> count_wrong(n + 2, 0);
    for (int p = 1; p <= n + 1; p++) {
        int d = pole_color[p];
        if (d == 0) continue;
        for (int b : poles[p]) {
            if (b != d) count_wrong[p]++;
        }
    }

    int empty_pole = -1;
    for (int p = 1; p <= n + 1; p++) {
        if (pole_color[p] == 0) {
            empty_pole = p;
            break;
        }
    }

    auto find_temp = [&](int x) -> pair<int, bool> {
        if (empty_pole != x && poles[empty_pole].size() < m) {
            return {empty_pole, true};
        }
        for (int y = 1; y <= n + 1; y++) {
            if (y != x && poles[y].size() < m) {
                return {y, false};
            }
        }
        assert(false);
        return {-1, false};
    };

    auto is_done = [&]() -> bool {
        for (int c = 1; c <= n; c++) {
            int p = target[c];
            int correct = (int)poles[p].size() - count_wrong[p];
            if (correct != m) return false;
        }
        return true;
    };

    vector<pair<int, int>> moves;

    auto perform_move = [&](int x, int y, int col) {
        poles[x].pop_back();
        int dx = pole_color[x];
        if (dx > 0 && col != dx) count_wrong[x]--;
        poles[y].push_back(col);
        int dy = pole_color[y];
        if (dy > 0 && col != dy) count_wrong[y]++;
        moves.emplace_back(x, y);
    };

    while (moves.size() < 2000000 && !is_done()) {
        bool did_move = false;

        // Pri1 clean to target
        for (int x = 1; x <= n + 1 && !did_move; x++) {
            if (poles[x].empty()) continue;
            int col = poles[x].back();
            int y = target[col];
            if (y == x) continue;
            if (poles[y].size() < m) {
                bool clean = poles[y].empty() || poles[y].back() == col;
                if (clean) {
                    perform_move(x, y, col);
                    did_move = true;
                }
            }
        }
        if (did_move) continue;

        // Pri1 non-clean to target
        for (int x = 1; x <= n + 1 && !did_move; x++) {
            if (poles[x].empty()) continue;
            int col = poles[x].back();
            int y = target[col];
            if (y == x) continue;
            if (poles[y].size() < m) {
                bool clean = poles[y].empty() || poles[y].back() == col;
                if (!clean) {
                    perform_move(x, y, col);
                    did_move = true;
                }
            }
        }
        if (did_move) continue;

        // Pri2 digging: correct top on target with wrong inside
        for (int x = 1; x <= n + 1 && !did_move; x++) {
            int dx = pole_color[x];
            if (dx == 0 || poles[x].empty()) continue;
            int col = poles[x].back();
            if (col != dx || count_wrong[x] == 0) continue;
            auto [ty, _] = find_temp(x);
            if (ty != -1) {
                perform_move(x, ty, col);
                did_move = true;
            }
        }
        if (did_move) continue;

        // Pri3: wrong top on target or any on empty_pole
        for (int x = 1; x <= n + 1 && !did_move; x++) {
            int dx = pole_color[x];
            if (poles[x].empty()) continue;
            int col = poles[x].back();
            bool is_wrong = (dx > 0 && col != dx) || (dx == 0);
            if (!is_wrong) continue;
            auto [ty, _] = find_temp(x);
            if (ty != -1) {
                perform_move(x, ty, col);
                did_move = true;
            }
        }
        if (did_move) continue;

        // Pri4: any move to temp
        for (int x = 1; x <= n + 1 && !did_move; x++) {
            if (poles[x].empty()) continue;
            int col = poles[x].back();
            auto [ty, _] = find_temp(x);
            if (ty != -1) {
                perform_move(x, ty, col);
                did_move = true;
            }
        }
        if (did_move) continue;

        // If no move, break
        break;
    }

    cout << moves.size() << endl;
    for (auto& mv : moves) {
        cout << mv.first << " " << mv.second << endl;
    }

    return 0;
}