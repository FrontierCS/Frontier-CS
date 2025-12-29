#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

int n;
size_t m;
vector<vector<int>> poles;
vector<pair<int, int>> moves;

void move_ball(int from, int to) {
    if (from == to) return;
    if (poles[from].empty()) return;
    if (poles[to].size() >= m) return;

    int ball = poles[from].back();
    poles[from].pop_back();
    poles[to].push_back(ball);
    moves.push_back({from, to});
}

bool is_pole_sorted(int p_idx) {
    if (poles[p_idx].size() != m) {
        return false;
    }
    for (int ball : poles[p_idx]) {
        if (ball != p_idx) {
            return false;
        }
    }
    return true;
}

bool can_place_on(int p_idx) {
    if (poles[p_idx].empty()) {
        return true;
    }
    if (poles[p_idx].size() < m) {
        for (int ball : poles[p_idx]) {
            if (ball != p_idx) {
                return false;
            }
        }
        return true;
    }
    return false;
}

bool is_top_ball_settled(int p_idx) {
    if (poles[p_idx].empty()) {
        return false;
    }
    int top_ball_color = poles[p_idx].back();
    if (top_ball_color != p_idx) {
        return false;
    }
    for (int ball : poles[p_idx]) {
        if (ball != p_idx) {
            return false;
        }
    }
    return true;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int m_int;
    cin >> n >> m_int;
    m = m_int;

    poles.resize(n + 2);
    for (int i = 1; i <= n; ++i) {
        poles[i].resize(m);
        for (size_t j = 0; j < m; ++j) {
            cin >> poles[i][j];
        }
    }

    vector<bool> sorted_poles(n + 1, false);

    while (true) {
        bool all_sorted = true;
        for (int i = 1; i <= n; ++i) {
            if (!sorted_poles[i] && is_pole_sorted(i)) {
                sorted_poles[i] = true;
            }
            if (!sorted_poles[i]) {
                all_sorted = false;
            }
        }
        if (all_sorted) {
            break;
        }

        bool move_made_in_placing = false;
        // Phase 1: Try to make "placing" moves.
        for (int i = 1; i <= n + 1; ++i) {
            if (poles[i].empty()) continue;
            
            int ball_color = poles[i].back();
            if (i == ball_color) continue;
            
            if (can_place_on(ball_color)) {
                move_ball(i, ball_color);
                move_made_in_placing = true;
            }
        }
        if (move_made_in_placing) continue;

        // Phase 2: If no placing moves, make a "clearing" move.
        int clear_from = -1;
        for (int i = 1; i <= n; ++i) {
            if (!sorted_poles[i] && !poles[i].empty() && !is_top_ball_settled(i)) {
                clear_from = i;
                break;
            }
        }
        
        if (clear_from == -1 && !poles[n+1].empty()) {
             clear_from = n + 1;
        }

        if (clear_from != -1) {
            int move_to = -1;
            if (poles[n+1].size() < m) {
                move_to = n + 1;
            } else {
                for (int i = 1; i <= n; ++i) {
                    if (i != clear_from && poles[i].size() < m) {
                        move_to = i;
                        break;
                    }
                }
            }
            if (move_to != -1) {
                move_ball(clear_from, move_to);
            }
        }
    }

    cout << moves.size() << "\n";
    for (const auto& p : moves) {
        cout << p.first << " " << p.second << "\n";
    }

    return 0;
}