#include <iostream>
#include <vector>
#include <utility>
#include <numeric>
#include <algorithm>

using namespace std;

int n, m;
vector<vector<int>> poles;
vector<pair<int, int>> moves;

void do_move(int from, int to) {
    if (from == to) return;

    if (poles[from - 1].empty()) return;
    if (poles[to - 1].size() >= m) return;

    int ball = poles[from - 1].back();
    poles[from - 1].pop_back();
    poles[to - 1].push_back(ball);
    moves.push_back({from, to});
}

void move_from_pole_to_buffer(int p, int buf_pole) {
    if (poles[buf_pole - 1].size() == m) {
        int top_ball_color = poles[buf_pole - 1].back();
        int target_pole = top_ball_color;

        if (poles[target_pole - 1].size() < m) {
            do_move(buf_pole, target_pole);
        } else {
            int new_dest = -1;
            for (int i = 1; i <= n; ++i) {
                if (i != p && poles[i - 1].size() < m) {
                    new_dest = i;
                    break;
                }
            }
            // A non-full pole must exist because total balls < total capacity
            do_move(buf_pole, new_dest);
        }
    }
    do_move(p, buf_pole);
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

    // Simple target assignment: pole i is for color i.
    vector<int> pole_target_color(n + 1);
    iota(pole_target_color.begin(), pole_target_color.end(), 0);

    // Calculate the length of the "happy prefix" for each pole.
    // A happy prefix on pole `i` is a sequence of balls of color `i` from the bottom.
    vector<int> happy_prefix_len(n + 1);
    for (int i = 1; i <= n; ++i) {
        int current_h = 0;
        for (size_t j = 0; j < poles[i - 1].size(); ++j) {
            if (poles[i - 1][j] == pole_target_color[i]) {
                current_h++;
            } else {
                break;
            }
        }
        happy_prefix_len[i] = current_h;
    }

    // Phase 1: Move all "unhappy" balls to the buffer pole (n+1).
    for (int i = 1; i <= n; ++i) {
        while (poles[i - 1].size() > (size_t)happy_prefix_len[i]) {
            move_from_pole_to_buffer(i, n + 1);
        }
    }

    // Phase 2: Drain the buffer pole, moving balls to their correct destination poles.
    while (!poles[n].empty()) {
        int ball_color = poles[n].back();
        int dest_pole = ball_color;
        do_move(n + 1, dest_pole);
    }

    cout << moves.size() << "\n";
    for (const auto& move : moves) {
        cout << move.first << " " << move.second << "\n";
    }

    return 0;
}