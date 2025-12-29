#include <iostream>
#include <vector>
#include <utility>
#include <numeric>
#include <algorithm>

using namespace std;

int n, m;
vector<vector<int>> poles;
vector<pair<int, int>> moves;

void perform_move(int from, int to) {
    if (from == to) return;
    if (poles[from - 1].empty()) return;
    if (poles[to - 1].size() >= m) return;

    int ball = poles[from - 1].back();
    poles[from - 1].pop_back();
    poles[to - 1].push_back(ball);
    moves.push_back({from, to});
}

// Find a pole that is not full, excluding specified poles.
int find_space(int excluded1, int excluded2 = -1) {
    for (int i = 1; i <= n + 1; ++i) {
        if (i != excluded1 && i != excluded2 && poles[i - 1].size() < m) {
            return i;
        }
    }
    return -1; // Should not happen in a valid state
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n >> m;
    poles.resize(n + 1);
    for (int i = 0; i < n; ++i) {
        poles[i].resize(m);
        for (int j = 0; j < m; ++j) {
            cin >> poles[i][j];
        }
    }

    for (int c = 1; c <= n; ++c) {
        int target_pole = c;

        // Phase 1: Clear target_pole of balls that are not color c
        while (true) {
            bool all_correct_or_empty = true;
            for (int ball : poles[c - 1]) {
                if (ball != c) {
                    all_correct_or_empty = false;
                    break;
                }
            }
            if (all_correct_or_empty) break;

            int top_ball = poles[c - 1].back();
            if (top_ball == c) {
                // Correct ball is on top of incorrect ones. Move it away temporarily.
                int temp_pole = find_space(c);
                perform_move(c, temp_pole);
            } else {
                // Incorrect ball on top. Move it to its home pole or a temp pole.
                int home_pole = top_ball;
                if (poles[home_pole - 1].size() < m) {
                    perform_move(c, home_pole);
                } else {
                    int temp_pole = find_space(c, home_pole);
                    perform_move(c, temp_pole);
                }
            }
        }

        // Phase 2: Gather all balls of color c to target_pole
        while (poles[c - 1].size() < m) {
            bool found_on_top = false;
            // First, check for any c-ball that is already on top of a pole
            for (int p = 1; p <= n + 1; ++p) {
                if (p == c) continue;
                if (!poles[p - 1].empty() && poles[p - 1].back() == c) {
                    perform_move(p, c);
                    found_on_top = true;
                    break;
                }
            }
            if (found_on_top) continue;

            // If no c-ball is on top, find one closest to the top and unbury it
            int best_p = -1, min_dist = m + 1;
            for (int p = 1; p <= n + 1; ++p) {
                if (p == c) continue;
                for (int i = poles[p - 1].size() - 1; i >= 0; --i) {
                    if (poles[p - 1][i] == c) {
                        int dist = poles[p - 1].size() - 1 - i;
                        if (dist < min_dist) {
                            min_dist = dist;
                            best_p = p;
                        }
                        break; 
                    }
                }
            }

            if (best_p != -1) {
                // Unbury the ball
                while (poles[best_p - 1].back() != c) {
                    int top_ball_color = poles[best_p - 1].back();
                    int home_pole = top_ball_color;
                    if (home_pole != best_p && poles[home_pole - 1].size() < m) {
                        perform_move(best_p, home_pole);
                    } else {
                        int temp_pole = find_space(best_p, c);
                        perform_move(best_p, temp_pole);
                    }
                }
                perform_move(best_p, c);
            } else {
                // All balls of color c are now on the target pole
                break;
            }
        }
    }

    cout << moves.size() << "\n";
    for (const auto& p : moves) {
        cout << p.first << " " << p.second << "\n";
    }

    return 0;
}