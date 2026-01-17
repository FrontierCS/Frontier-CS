#include <bits/stdc++.h>
using namespace std;

using ull = unsigned long long;

struct Veh {
    int id, len;
    bool horiz;
    int fixed, min_pos, max_pos;
};

struct Move {
    int veh_id;
    char dir;
};

vector<int> get_pos(ull k, int nn) {
    vector<int> res(nn);
    for (int i = 0; i < nn; i++) {
        res[i] = k % 8;
        k /= 8;
    }
    return res;
}

int main() {
    vector<vector<int>> board(6, vector<int>(6));
    for (int r = 0; r < 6; r++) {
        for (int c = 0; c < 6; c++) {
            cin >> board[r][c];
        }
    }

    bool visited[6][6] = {false};
    vector<Veh> all_vehs;
    vector<int> init_pos;
    int red_idx = -1;
    for (int r = 0; r < 6; r++) {
        for (int c = 0; c < 6; c++) {
            if (board[r][c] == 0 || visited[r][c]) continue;
            int id = board[r][c];
            int len_h = 1;
            for (int cc = c + 1; cc < 6; cc++) {
                if (board[r][cc] == id) len_h++;
                else break;
            }
            int len_v = 1;
            for (int rr = r + 1; rr < 6; rr++) {
                if (board[rr][c] == id) len_v++;
                else break;
            }
            bool horiz;
            int len;
            int start_pos;
            if (len_h >= 2 && len_v == 1) {
                horiz = true;
                len = len_h;
                start_pos = c;
                for (int k = 0; k < len; k++) visited[r][c + k] = true;
            } else if (len_v >= 2 && len_h == 1) {
                horiz = false;
                len = len_v;
                start_pos = r;
                for (int k = 0; k < len; k++) visited[r + k][c] = true;
            } else {
                continue;
            }
            int fixed = horiz ? r : c;
            int minp = 0;
            int maxp = 6 - len;
            all_vehs.push_back({id, len, horiz, fixed, minp, maxp});
            init_pos.push_back(start_pos);
            int idx = all_vehs.size() - 1;
            if (id == 1) red_idx = idx;
        }
    }
    int n = all_vehs.size();

    vector<ull> pow8(n + 1, 0);
    pow8[0] = 1;
    for (int i = 1; i <= n; i++) {
        pow8[i] = pow8[i - 1] * 8ULL;
    }

    // Backward BFS for solve_dist
    unordered_map<ull, int> solve_dist;
    queue<ull> qb;

    // Enumerate states with red at 5
    vector<int> other_ids;
    for (int i = 0; i < n; i++) if (i != red_idx) other_ids.push_back(i);
    int num_other = other_ids.size();

    vector<int> pos_gen(n, 0);
    function<void(int)> gen = [&](int oidx) {
        if (oidx == num_other) {
            pos_gen[red_idx] = 5;
            ull key = 0;
            for (int j = 0; j < n; j++) {
                key = key * 8 + pos_gen[j];
            }
            vector<vector<int>> temp(6, vector<int>(6, 0));
            bool val = true;
            for (int j = 0; j < n && val; j++) {
                auto& v = all_vehs[j];
                int p = pos_gen[j];
                if (v.horiz) {
                    for (int jj = 0; jj < v.len; jj++) {
                        int cc = p + jj;
                        if (cc > 5) continue;
                        int rr = v.fixed;
                        if (temp[rr][cc] != 0) {
                            val = false;
                            break;
                        }
                        temp[rr][cc] = v.id;
                    }
                } else {
                    for (int jj = 0; jj < v.len; jj++) {
                        int rr = p + jj;
                        if (rr > 5) continue;
                        int cc = v.fixed;
                        if (temp[rr][cc] != 0) {
                            val = false;
                            break;
                        }
                        temp[rr][cc] = v.id;
                    }
                }
            }
            if (val && solve_dist.find(key) == solve_dist.end()) {
                solve_dist[key] = 1;
                qb.push(key);
            }
            return;
        }
        int i = other_ids[oidx];
        auto& v = all_vehs[i];
        for (int p = v.min_pos; p <= v.max_pos; p++) {
            pos_gen[i] = p;
            gen(oidx + 1);
        }
    };
    gen(0);

    // Continue backward BFS
    while (!qb.empty()) {
        ull ck = qb.front();
        qb.pop();
        int d = solve_dist[ck];
        vector<int> pos = get_pos(ck, n);
        vector<vector<int>> temp(6, vector<int>(6, 0));
        for (int j = 0; j < n; j++) {
            auto& v = all_vehs[j];
            int p = pos[j];
            if (v.horiz) {
                for (int jj = 0; jj < v.len; jj++) {
                    int cc = p + jj;
                    if (cc <= 5) {
                        temp[v.fixed][cc] = v.id;
                    }
                }
            } else {
                for (int jj = 0; jj < v.len; jj++) {
                    int rr = p + jj;
                    if (rr <= 5) {
                        temp[rr][v.fixed] = v.id;
                    }
                }
            }
        }
        for (int i = 0; i < n; i++) {
            auto& v = all_vehs[i];
            int oldp = pos[i];
            int maxp = (i == red_idx ? 5 : v.max_pos);
            // delta +1
            int np1 = oldp + 1;
            if (np1 <= maxp) {
                int gained = oldp + v.len;
                int gr, gc;
                if (v.horiz) {
                    gr = v.fixed;
                    gc = gained;
                } else {
                    gr = gained;
                    gc = v.fixed;
                }
                bool off = (gc > 5 || gr > 5);
                bool can = off ? (i == red_idx && v.horiz) : (temp[gr][gc] == 0);
                if (can) {
                    ull nk = ck + pow8[i];
                    if (solve_dist.find(nk) == solve_dist.end()) {
                        solve_dist[nk] = d + 1;
                        qb.push(nk);
                    }
                }
            }
            // delta -1
            int np2 = oldp - 1;
            if (np2 >= 0) {
                int gained = np2;
                int gr, gc;
                if (v.horiz) {
                    gr = v.fixed;
                    gc = gained;
                } else {
                    gr = gained;
                    gc = v.fixed;
                }
                bool can = (temp[gr][gc] == 0);
                if (can) {
                    ull nk = ck - pow8[i];
                    if (solve_dist.find(nk) == solve_dist.end()) {
                        solve_dist[nk] = d + 1;
                        qb.push(nk);
                    }
                }
            }
        }
    }

    // Initial key
    ull init_key = 0;
    for (int p : init_pos) {
        init_key = init_key * 8 + p;
    }
    int max_min_steps = solve_dist[init_key];

    // Forming BFS
    queue<ull> qf;
    unordered_map<ull, int> form_depth;
    unordered_map<ull, pair<ull, Move>> parent_form;
    qf.push(init_key);
    form_depth[init_key] = 0;
    ull best_key = init_key;
    max_min_steps = solve_dist[init_key];

    while (!qf.empty()) {
        ull ck = qf.front();
        qf.pop();
        int fd = form_depth[ck];
        auto sit = solve_dist.find(ck);
        if (sit != solve_dist.end()) {
            int sd = sit->second;
            if (sd > max_min_steps) {
                max_min_steps = sd;
                best_key = ck;
            }
        }
        vector<int> posf = get_pos(ck, n);
        vector<vector<int>> tempf(6, vector<int>(6, 0));
        for (int j = 0; j < n; j++) {
            auto& v = all_vehs[j];
            int p = posf[j];
            if (v.horiz) {
                for (int jj = 0; jj < v.len; jj++) {
                    int cc = p + jj;
                    if (cc <= 5) {
                        tempf[v.fixed][cc] = v.id;
                    }
                }
            } else {
                for (int jj = 0; jj < v.len; jj++) {
                    int rr = p + jj;
                    if (rr <= 5) {
                        tempf[rr][v.fixed] = v.id;
                    }
                }
            }
        }
        for (int i = 0; i < n; i++) {
            auto& v = all_vehs[i];
            int oldp = posf[i];
            int maxp = (i == red_idx ? 5 : v.max_pos);
            // +1
            int np = oldp + 1;
            if (np <= maxp) {
                int gained = oldp + v.len;
                int gr, gc;
                if (v.horiz) {
                    gr = v.fixed;
                    gc = gained;
                } else {
                    gr = gained;
                    gc = v.fixed;
                }
                bool off = (gc > 5 || gr > 5);
                bool can = off ? (i == red_idx && v.horiz) : (tempf[gr][gc] == 0);
                if (can) {
                    ull nk = ck + pow8[i];
                    if (form_depth.find(nk) == form_depth.end()) {
                        form_depth[nk] = fd + 1;
                        char dirc = v.horiz ? 'R' : 'D';
                        parent_form[nk] = {ck, {v.id, dirc}};
                        qf.push(nk);
                    }
                }
            }
            // -1
            np = oldp - 1;
            if (np >= 0) {
                int gained = np;
                int gr, gc;
                if (v.horiz) {
                    gr = v.fixed;
                    gc = gained;
                } else {
                    gr = gained;
                    gc = v.fixed;
                }
                bool can = (tempf[gr][gc] == 0);
                if (can) {
                    ull nk = ck - pow8[i];
                    if (form_depth.find(nk) == form_depth.end()) {
                        form_depth[nk] = fd + 1;
                        char dirc = v.horiz ? 'L' : 'U';
                        parent_form[nk] = {ck, {v.id, dirc}};
                        qf.push(nk);
                    }
                }
            }
        }
    }

    // Reconstruct
    vector<pair<int, char>> move_list;
    ull current = best_key;
    while (current != init_key) {
        auto p = parent_form[current];
        move_list.push_back({p.second.veh_id, p.second.dir});
        current = p.first;
    }
    reverse(move_list.begin(), move_list.end());

    cout << max_min_steps << " " << move_list.size() << endl;
    for (auto& m : move_list) {
        cout << m.first << " " << m.second << endl;
    }

    return 0;
}