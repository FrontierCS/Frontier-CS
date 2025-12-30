#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, m;
    cin >> n >> m;
    vector<vector<int>> poles(n + 2);
    vector<int> target(n + 1);
    for (int c = 1; c <= n; ++c) target[c] = c;
    vector<vector<int>> color_count(n + 2, vector<int>(n + 1, 0));
    for (int i = 1; i <= n; ++i) {
        poles[i].resize(m);
        for (int j = 0; j < m; ++j) {
            cin >> poles[i][j];
            color_count[i][poles[i][j]]++;
        }
    }
    vector<pair<int, int>> moves;
    auto do_move = [&](int x, int y) -> bool {
        if (poles[x].empty()) return false;
        int c = poles[x].back();
        poles[x].pop_back();
        color_count[x][c]--;
        poles[y].push_back(c);
        color_count[y][c]++;
        moves.emplace_back(x, y);
        return true;
    };
    auto is_complete = [&](int p) -> bool {
        if (poles[p].size() != static_cast<size_t>(m)) return false;
        return color_count[p][p] == m;
    };
    auto get_fraction = [&](int p) -> double {
        if (poles[p].empty()) return 0.0;
        return static_cast<double>(color_count[p][p]) / poles[p].size();
    };
    auto top_color = [&](int p) -> int {
        if (poles[p].empty()) return -1;
        return poles[p].back();
    };
    auto is_done = [&]() -> bool {
        for (int c = 1; c <= n; ++c) {
            if (color_count[target[c]][c] != m) return false;
        }
        return true;
    };
    int buf = n + 1;
    while (!is_done() && moves.size() < 2000000) {
        // Try good move
        int best_x = -1, best_y = -1, best_size = INT_MAX;
        for (int x = 1; x <= n + 1; ++x) {
            if (poles[x].empty()) continue;
            int c = top_color(x);
            int y = target[c];
            if (x != y && poles[y].size() < static_cast<size_t>(m)) {
                int sz = poles[x].size();
                if (sz < best_size) {
                    best_size = sz;
                    best_x = x;
                    best_y = y;
                }
            }
        }
        if (best_x != -1) {
            do_move(best_x, best_y);
            continue;
        }
        // Stir
        bool did_stir = false;
        // Try move to buffer if space
        if (poles[buf].size() < static_cast<size_t>(m)) {
            // Prefer mismatched top
            int chosen_x = -1;
            double min_frac = 2.0;
            int max_sz = -1;
            for (int x = 1; x <= n + 1; ++x) {
                if (x == buf || poles[x].empty()) continue;
                int c = top_color(x);
                if (target[c] != x) {
                    double f = get_fraction(x);
                    int sz = poles[x].size();
                    if (f < min_frac || (abs(f - min_frac) < 1e-9 && sz > max_sz)) {
                        min_frac = f;
                        max_sz = sz;
                        chosen_x = x;
                    }
                }
            }
            if (chosen_x == -1) {
                // No mismatched, prefer poles with wrong inside (f < 1 and not complete)
                min_frac = 2.0;
                max_sz = -1;
                for (int x = 1; x <= n + 1; ++x) {
                    if (x == buf || poles[x].empty() || is_complete(x)) continue;
                    double f = get_fraction(x);
                    if (f < 1.0 - 1e-9) {
                        int sz = poles[x].size();
                        if (f < min_frac || (abs(f - min_frac) < 1e-9 && sz > max_sz)) {
                            min_frac = f;
                            max_sz = sz;
                            chosen_x = x;
                        }
                    }
                }
            }
            if (chosen_x != -1) {
                do_move(chosen_x, buf);
                did_stir = true;
                continue;
            }
        }
        // Move from buffer to some y
        if (!poles[buf].empty()) {
            int c = top_color(buf);
            int good_y = target[c];
            if (good_y != buf && poles[good_y].size() < static_cast<size_t>(m)) {
                do_move(buf, good_y);
                did_stir = true;
                continue;
            }
            // No good y, choose y with most space (smallest size)
            int chosen_y = -1;
            int min_sz = INT_MAX;
            for (int y = 1; y <= n + 1; ++y) {
                if (y == buf || poles[y].size() == static_cast<size_t>(m)) continue;
                int sz = poles[y].size();
                if (sz < min_sz) {
                    min_sz = sz;
                    chosen_y = y;
                }
            }
            if (chosen_y != -1) {
                do_move(buf, chosen_y);
                did_stir = true;
                continue;
            }
        }
        // If no stir possible, break
        if (!did_stir) break;
    }
    cout << moves.size() << endl;
    for (auto& mv : moves) {
        cout << mv.first << " " << mv.second << endl;
    }
    return 0;
}