#include <iostream>
#include <vector>
#include <utility>
#include <cmath>
#include <algorithm>

using namespace std;

const int N = 20;

vector<pair<char, char>> generate_moves(int si, int sj, int ti, int tj) {
    vector<pair<char, char>> seq;
    int di = ti - si;
    int dj = tj - sj;
    char ver_dir = (di > 0 ? 'D' : 'U');
    char hor_dir = (dj > 0 ? 'R' : 'L');
    for (int i = 0; i < abs(di); ++i) seq.push_back({'M', ver_dir});
    for (int j = 0; j < abs(dj); ++j) seq.push_back({'M', hor_dir});
    return seq;
}

vector<pair<char, char>> get_actions(int ci, int cj, int ti, int tj) {
    vector<pair<char, char>> best_seq;
    int min_cost = 1e9;

    // Plan 0: direct moves
    auto seq0 = generate_moves(ci, cj, ti, tj);
    int cost0 = seq0.size();
    if (cost0 < min_cost) {
        min_cost = cost0;
        best_seq = seq0;
    }

    // Plan 1: slide to a boundary then move
    vector<pair<char, pair<int, int>>> dirs = {
        {'L', {ci, 0}},
        {'R', {ci, N-1}},
        {'U', {0, cj}},
        {'D', {N-1, cj}}
    };
    for (auto& p : dirs) {
        char dir = p.first;
        int ni = p.second.first;
        int nj = p.second.second;
        bool feasible = false;
        if (dir == 'L' && cj > 0) feasible = true;
        if (dir == 'R' && cj < N-1) feasible = true;
        if (dir == 'U' && ci > 0) feasible = true;
        if (dir == 'D' && ci < N-1) feasible = true;
        if (!feasible) continue;
        int dist = abs(ni - ti) + abs(nj - tj);
        int cost = 1 + dist;
        if (cost < min_cost) {
            vector<pair<char, char>> seq;
            seq.push_back({'S', dir});
            auto moves = generate_moves(ni, nj, ti, tj);
            seq.insert(seq.end(), moves.begin(), moves.end());
            min_cost = cost;
            best_seq = seq;
        }
    }

    // Plan 2: two slides to a corner then move
    vector<pair<int, int>> corners = {{0,0}, {0,N-1}, {N-1,0}, {N-1,N-1}};
    for (auto& corner : corners) {
        int r_c = corner.first;
        int c_c = corner.second;

        // horizontal then vertical
        bool h_first_feasible = false;
        if ((c_c == 0 && cj > 0) || (c_c == N-1 && cj < N-1)) {
            int newi_h = ci;
            int newj_h = c_c;
            if ((r_c == 0 && newi_h > 0) || (r_c == N-1 && newi_h < N-1)) {
                if (newi_h != r_c) {
                    h_first_feasible = true;
                }
            }
        }
        if (h_first_feasible) {
            int dist = abs(r_c - ti) + abs(c_c - tj);
            int cost = 2 + dist;
            if (cost < min_cost) {
                vector<pair<char, char>> seq;
                char dir_h = (c_c == 0 ? 'L' : 'R');
                seq.push_back({'S', dir_h});
                char dir_v = (r_c == 0 ? 'U' : 'D');
                seq.push_back({'S', dir_v});
                auto moves = generate_moves(r_c, c_c, ti, tj);
                seq.insert(seq.end(), moves.begin(), moves.end());
                min_cost = cost;
                best_seq = seq;
            }
        }

        // vertical then horizontal
        bool v_first_feasible = false;
        if ((r_c == 0 && ci > 0) || (r_c == N-1 && ci < N-1)) {
            int newi_v = r_c;
            int newj_v = cj;
            if ((c_c == 0 && newj_v > 0) || (c_c == N-1 && newj_v < N-1)) {
                if (newj_v != c_c) {
                    v_first_feasible = true;
                }
            }
        }
        if (v_first_feasible) {
            int dist = abs(r_c - ti) + abs(c_c - tj);
            int cost = 2 + dist;
            if (cost < min_cost) {
                vector<pair<char, char>> seq;
                char dir_v = (r_c == 0 ? 'U' : 'D');
                seq.push_back({'S', dir_v});
                char dir_h = (c_c == 0 ? 'L' : 'R');
                seq.push_back({'S', dir_h});
                auto moves = generate_moves(r_c, c_c, ti, tj);
                seq.insert(seq.end(), moves.begin(), moves.end());
                min_cost = cost;
                best_seq = seq;
            }
        }
    }

    return best_seq;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N_in, M;
    cin >> N_in >> M; // N_in is always 20, M is always 40
    vector<int> i_pts(M), j_pts(M);
    for (int k = 0; k < M; ++k) {
        cin >> i_pts[k] >> j_pts[k];
    }

    int ci = i_pts[0], cj = j_pts[0];
    for (int k = 1; k < M; ++k) {
        int ti = i_pts[k], tj = j_pts[k];
        auto actions = get_actions(ci, cj, ti, tj);
        for (auto& act : actions) {
            cout << act.first << " " << act.second << "\n";
        }
        ci = ti;
        cj = tj;
    }

    return 0;
}