#include <bits/stdc++.h>
using namespace std;

struct Vehicle {
    int id;
    bool horizontal;
    int fixed;
    int len;
    int pos;
    int max_pos;
};

long long get_id(const vector<int>& pos, const vector<int>& base) {
    long long id = 0;
    long long mul = 1;
    for (int i = 0; i < pos.size(); ++i) {
        id += (long long)pos[i] * mul;
        mul *= base[i];
    }
    return id;
}

vector<int> decode(long long id, const vector<int>& base) {
    int nn = base.size();
    vector<int> pos(nn);
    for (int i = 0; i < nn; ++i) {
        pos[i] = id % base[i];
        id /= base[i];
    }
    return pos;
}

bool is_valid(const vector<int>& pos, const vector<Vehicle>& veh, bool allow_red_partial = true) {
    int nn = veh.size();
    char grid[36] = {0};
    auto idx = [](int r, int c) { return r * 6 + c; };
    for (int vi = 0; vi < nn; ++vi) {
        int p = pos[vi];
        const auto& v = veh[vi];
        if (vi == 0) { // red
            if (!allow_red_partial && (p < 0 || p > 4)) return false;
            int r = 2;
            for (int cc = 0; cc < 2; ++cc) {
                int c = p + cc;
                if (c < 0 || c > 5) continue;
                int ii = idx(r, c);
                if (grid[ii] != 0) return false;
                grid[ii] = 1;
            }
        } else {
            int llen = v.len;
            if (p < 0 || p + llen - 1 > 5) return false;
            if (v.horizontal) {
                int r = v.fixed;
                for (int cc = 0; cc < llen; ++cc) {
                    int c = p + cc;
                    int ii = idx(r, c);
                    if (grid[ii] != 0) return false;
                    grid[ii] = 1;
                }
            } else {
                int c = v.fixed;
                for (int rr = 0; rr < llen; ++rr) {
                    int r = p + rr;
                    int ii = idx(r, c);
                    if (grid[ii] != 0) return false;
                    grid[ii] = 1;
                }
            }
        }
    }
    return true;
}

bool can_move(int vi, int delta, const vector<int>& pos, const vector<Vehicle>& veh, const char grid[36]) {
    int curp = pos[vi];
    int np = curp + delta;
    const auto& v = veh[vi];
    int llen = v.len;
    auto idx = [](int r, int c) { return r * 6 + c; };
    if (v.horizontal) {
        int r = v.fixed;
        if (delta == 1) {
            int new_right = np + llen - 1;
            if (new_right > 5) return (vi == 0);
            return (grid[idx(r, new_right)] == 0);
        } else {
            int new_left = np;
            if (new_left < 0) return false;
            return (grid[idx(r, new_left)] == 0);
        }
    } else {
        int c = v.fixed;
        if (delta == 1) {
            int new_bottom = np + llen - 1;
            if (new_bottom > 5) return false;
            return (grid[idx(new_bottom, c)] == 0);
        } else {
            int new_top = np;
            if (new_top < 0) return false;
            return (grid[idx(new_top, c)] == 0);
        }
    }
}

int main() {
    vector<vector<int>> board(6, vector<int>(6));
    for (int i = 0; i < 6; ++i) {
        for (int j = 0; j < 6; ++j) {
            cin >> board[i][j];
        }
    }

    // Parse vehicles
    vector<Vehicle> vehicles;
    set<int> used;
    for (int i = 0; i < 6; ++i) {
        for (int j = 0; j < 6; ++j) {
            int idd = board[i][j];
            if (idd > 0 && used.find(idd) == used.end()) {
                used.insert(idd);
                vector<pair<int, int>> parts;
                for (int x = 0; x < 6; ++x) {
                    for (int y = 0; y < 6; ++y) {
                        if (board[x][y] == idd) parts.emplace_back(x, y);
                    }
                }
                int np = parts.size();
                bool same_row = true, same_col = true;
                int r0 = parts[0].first, c0 = parts[0].second;
                for (auto& pr : parts) {
                    if (pr.first != r0) same_row = false;
                    if (pr.second != c0) same_col = false;
                }
                assert(same_row != same_col);
                Vehicle v{idd, same_row, same_row ? r0 : c0, np, 0};
                if (same_row) {
                    sort(parts.begin(), parts.end(), [](auto a, auto b) { return a.second < b.second; });
                    v.pos = parts[0].second;
                    for (int k = 1; k < np; ++k) {
                        assert(parts[k].second == parts[0].second + k);
                    }
                } else {
                    sort(parts.begin(), parts.end(), [](auto a, auto b) { return a.first < b.first; });
                    v.pos = parts[0].first;
                    for (int k = 1; k < np; ++k) {
                        assert(parts[k].first == parts[0].first + k);
                    }
                }
                vehicles.push_back(v);
            }
        }
    }
    sort(vehicles.begin(), vehicles.end(), [](const Vehicle& a, const Vehicle& b) { return a.id < b.id; });
    int n = vehicles.size();
    vector<Vehicle> veh = vehicles;
    for (int i = 0; i < n; ++i) {
        veh[i].max_pos = 6 - veh[i].len;
        if (i == 0) {
            assert(veh[0].id == 1 && veh[0].horizontal && veh[0].fixed == 2 && veh[0].len == 2);
        }
    }

    // Initial pos
    vector<int> init_pos(n);
    for (int i = 0; i < n; ++i) init_pos[i] = veh[i].pos;

    // Solve bases
    vector<int> base_solve(n);
    base_solve[0] = 7;
    for (int i = 1; i < n; ++i) base_solve[i] = veh[i].max_pos + 1;
    long long total_solve = 1;
    for (int b : base_solve) total_solve *= b;

    // dist_solve
    vector<int> dist_solve(total_solve, -1);
    queue<long long> qs;

    // Enumerate goal states
    long long num_others = 1;
    for (int i = 1; i < n; ++i) num_others *= base_solve[i];
    vector<int> epos(n);
    for (long long conf = 0; conf < num_others; ++conf) {
        long long temp = conf;
        for (int i = 1; i < n; ++i) {
            epos[i] = temp % base_solve[i];
            temp /= base_solve[i];
        }
        epos[0] = 6;
        if (is_valid(epos, veh, true)) {
            long long sid = get_id(epos, base_solve);
            if (dist_solve[sid] == -1) {
                dist_solve[sid] = 0;
                qs.push(sid);
            }
        }
    }

    // Backward BFS for solve (actually forward dist to goal)
    while (!qs.empty()) {
        long long cid = qs.front(); qs.pop();
        int cd = dist_solve[cid];
        vector<int> pos = decode(cid, base_solve);

        // Build current grid
        char cgrid[36] = {0};
        auto idx = [](int r, int c) { return r * 6 + c; };
        for (int vi = 0; vi < n; ++vi) {
            int p = pos[vi];
            if (vi == 0) {
                int r = 2;
                for (int cc = 0; cc < 2; ++cc) {
                    int c = p + cc;
                    if (c >= 0 && c <= 5) cgrid[idx(r, c)] = 1;
                }
            } else {
                const auto& v = veh[vi];
                if (v.horizontal) {
                    int r = v.fixed;
                    for (int cc = 0; cc < v.len; ++cc) {
                        int c = p + cc;
                        cgrid[idx(r, c)] = 1;
                    }
                } else {
                    int c = v.fixed;
                    for (int rr = 0; rr < v.len; ++rr) {
                        int r = p + rr;
                        cgrid[idx(r, c)] = 1;
                    }
                }
            }
        }

        // Generate reverse moves
        for (int vi = 0; vi < n; ++vi) {
            int curp = pos[vi];
            for (int ddelta : {-1, 1}) {
                int np = curp + ddelta;
                if (np < 0) continue;
                bool range_ok = true;
                if (vi == 0) {
                    if (np > 6) range_ok = false;
                } else {
                    if (np > veh[vi].max_pos) range_ok = false;
                }
                if (!range_ok) continue;
                if (can_move(vi, ddelta, pos, veh, cgrid)) {
                    vector<int> newpos = pos;
                    newpos[vi] = np;
                    long long nid = get_id(newpos, base_solve);
                    if (dist_solve[nid] == -1) {
                        dist_solve[nid] = cd + 1;
                        qs.push(nid);
                    }
                }
            }
        }
    }

    // Now puzzle
    vector<int> base_puzzle(n);
    base_puzzle[0] = 5;
    for (int i = 1; i < n; ++i) base_puzzle[i] = base_solve[i];
    long long total_puzzle = 1;
    for (int b : base_puzzle) total_puzzle *= b;

    vector<int> reach(total_puzzle, -1);
    vector<int> prev_vi(total_puzzle, -1);
    vector<int> prev_delta(total_puzzle, 0);

    long long init_pid = get_id(init_pos, base_puzzle);
    reach[init_pid] = 0;

    queue<long long> qp;
    qp.push(init_pid);

    long long init_sid = get_id(init_pos, base_solve);
    int max_d = dist_solve[init_sid];
    long long best_pid = init_pid;
    int best_reach_steps = 0;

    // Forward BFS for reach
    while (!qp.empty()) {
        long long cid = qp.front(); qp.pop();
        int cr = reach[cid];
        vector<int> pos = decode(cid, base_puzzle);

        // Build current grid
        char cgrid[36] = {0};
        auto idx = [](int r, int c) { return r * 6 + c; };
        for (int vi = 0; vi < n; ++vi) {
            int p = pos[vi];
            if (vi == 0) {
                int r = 2;
                for (int cc = 0; cc < 2; ++cc) {
                    int c = p + cc;
                    if (c >= 0 && c <= 5) cgrid[idx(r, c)] = 1;
                }
            } else {
                const auto& v = veh[vi];
                if (v.horizontal) {
                    int r = v.fixed;
                    for (int cc = 0; cc < v.len; ++cc) {
                        int c = p + cc;
                        cgrid[idx(r, c)] = 1;
                    }
                } else {
                    int c = v.fixed;
                    for (int rr = 0; rr < v.len; ++rr) {
                        int r = p + rr;
                        cgrid[idx(r, c)] = 1;
                    }
                }
            }
        }

        // Generate moves
        for (int vi = 0; vi < n; ++vi) {
            int curp = pos[vi];
            for (int ddelta : {-1, 1}) {
                int np = curp + ddelta;
                if (np < 0) continue;
                bool range_ok = true;
                if (vi == 0) {
                    if (np > 4) range_ok = false;
                } else {
                    if (np > veh[vi].max_pos) range_ok = false;
                }
                if (!range_ok) continue;
                if (can_move(vi, ddelta, pos, veh, cgrid)) {
                    vector<int> newpos = pos;
                    newpos[vi] = np;
                    long long nid = get_id(newpos, base_puzzle);
                    if (reach[nid] == -1) {
                        reach[nid] = cr + 1;
                        prev_vi[nid] = vi;
                        prev_delta[nid] = ddelta;
                        qp.push(nid);

                        // Check if better
                        long long nsid = get_id(newpos, base_solve);
                        int nds = dist_solve[nsid];
                        if (nds > max_d) {
                            max_d = nds;
                            best_pid = nid;
                            best_reach_steps = reach[nid];
                        }
                    }
                }
            }
        }
    }

    // Output
    cout << max_d << " " << best_reach_steps << endl;

    if (best_reach_steps > 0) {
        vector<pair<int, char>> move_list;
        long long current = best_pid;
        while (reach[current] > 0) {
            int vi = prev_vi[current];
            int delta = prev_delta[current];
            int vid = veh[vi].id;
            char dir;
            if (veh[vi].horizontal) {
                dir = (delta == 1 ? 'R' : 'L');
            } else {
                dir = (delta == 1 ? 'D' : 'U');
            }
            move_list.emplace_back(vid, dir);
            vector<int> pos = decode(current, base_puzzle);
            pos[vi] -= delta;
            current = get_id(pos, base_puzzle);
        }
        reverse(move_list.begin(), move_list.end());
        for (auto& m : move_list) {
            cout << m.first << " " << m.second << endl;
        }
    }

    return 0;
}