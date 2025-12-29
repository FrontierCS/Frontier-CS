#include <bits/stdc++.h>
using namespace std;

struct Vehicle {
    int id;
    bool horiz;
    int len;
    int fixed;
    int pos;
    int max_pos;
    int num_p;
};

long long get_state(const vector<int>& p, const vector<int>& num_p) {
    long long s = 0;
    long long mul = 1;
    for (size_t i = 0; i < p.size(); ++i) {
        s += (long long)p[i] * mul;
        mul *= num_p[i];
    }
    return s;
}

vector<int> decode(long long s, const vector<int>& num_p) {
    vector<int> p(num_p.size());
    for (size_t i = 0; i < p.size(); ++i) {
        p[i] = s % num_p[i];
        s /= num_p[i];
    }
    return p;
}

void generate(int idx, vector<int>& pos, int temp_board[6][6], queue<long long>& q, vector<int>& solving_dist,
              const vector<Vehicle>& vehicles, const vector<int>& num_p, long long total) {
    int n = vehicles.size();
    if (idx == n) {
        long long st = get_state(pos, num_p);
        if (st < total && solving_dist[st] == -1) {
            solving_dist[st] = 0;
            q.push(st);
        }
        return;
    }
    const Vehicle& v = vehicles[idx];
    int l = v.len;
    bool h = v.horiz;
    int f = v.fixed;
    for (int p = 0; p < num_p[idx]; ++p) {
        vector<pair<int, int>> cells;
        bool can = true;
        for (int k = 0; k < l; ++k) {
            int r = h ? f : p + k;
            int c = h ? p + k : f;
            if (r >= 0 && r <= 5 && c >= 0 && c <= 5) {
                if (temp_board[r][c] != 0) {
                    can = false;
                    break;
                }
                cells.emplace_back(r, c);
            } else if (idx == 0 && h && c > 5 && r == f) {
                // allow red off right
            } else {
                can = false;
                break;
            }
        }
        if (can) {
            for (auto [r, c] : cells) temp_board[r][c] = 1;
            pos[idx] = p;
            generate(idx + 1, pos, temp_board, q, solving_dist, vehicles, num_p, total);
            for (auto [r, c] : cells) temp_board[r][c] = 0;
        }
    }
}

vector<tuple<int, int, char>> possible_moves(const vector<int>& pos, const vector<Vehicle>& vehicles) {
    vector<tuple<int, int, char>> res;
    int n = vehicles.size();
    for (int i = 0; i < n; ++i) {
        const Vehicle& v = vehicles[i];
        bool h = v.horiz;
        int curp = pos[i];
        int l = v.len;
        int f = v.fixed;
        int maxpp = (i == 0 && h) ? 6 : v.max_pos;
        // left/up
        {
            int newp = curp - 1;
            if (newp >= 0) {
                int target = newp;
                int tr = h ? f : target;
                int tc = h ? target : f;
                bool empty_t = true;
                for (int j = 0; j < n; ++j) {
                    if (j == i) continue;
                    const Vehicle& vj = vehicles[j];
                    bool hj = vj.horiz;
                    int fj = vj.fixed;
                    int pj = pos[j];
                    int lj = vj.len;
                    bool overlaps = false;
                    if (hj) {
                        if (fj == tr && pj <= tc && tc <= pj + lj - 1) overlaps = true;
                    } else {
                        if (fj == tc && pj <= tr && tr <= pj + lj - 1) overlaps = true;
                    }
                    if (overlaps) {
                        empty_t = false;
                        break;
                    }
                }
                if (empty_t) {
                    char dirr = h ? 'L' : 'U';
                    res.emplace_back(i, newp, dirr);
                }
            }
        }
        // right/down
        {
            int newp = curp + 1;
            if (newp > maxpp) continue;
            int target = curp + l;
            bool need = (target <= 5);
            int tr = h ? f : (need ? target : 0);
            int tc = h ? (need ? target : 0) : f;
            bool empty_t = true;
            if (need) {
                for (int j = 0; j < n; ++j) {
                    if (j == i) continue;
                    const Vehicle& vj = vehicles[j];
                    bool hj = vj.horiz;
                    int fj = vj.fixed;
                    int pj = pos[j];
                    int lj = vj.len;
                    bool overlaps = false;
                    if (hj) {
                        if (fj == tr && pj <= tc && tc <= pj + lj - 1) overlaps = true;
                    } else {
                        if (fj == tc && pj <= tr && tr <= pj + lj - 1) overlaps = true;
                    }
                    if (overlaps) {
                        empty_t = false;
                        break;
                    }
                }
                if (!empty_t) continue;
            } else {
                if (!(i == 0 && h)) continue;
            }
            char dirr = h ? 'R' : 'D';
            res.emplace_back(i, newp, dirr);
        }
    }
    return res;
}

int main() {
    vector<vector<int>> input_board(6, vector<int>(6));
    for (int i = 0; i < 6; ++i) {
        for (int j = 0; j < 6; ++j) {
            cin >> input_board[i][j];
        }
    }
    map<int, vector<pair<int, int>>> id_pos;
    for (int r = 0; r < 6; ++r) {
        for (int c = 0; c < 6; ++c) {
            int idd = input_board[r][c];
            if (idd > 0) {
                id_pos[idd].emplace_back(r, c);
            }
        }
    }
    vector<Vehicle> vehicles;
    // Parse red car
    auto it = id_pos.find(1);
    if (it != id_pos.end()) {
        auto& redpts = it->second;
        if (redpts.size() == 2) {
            int r1 = redpts[0].first, c1 = redpts[0].second;
            int r2 = redpts[1].first, c2 = redpts[1].second;
            if (r1 == r2 && r1 == 2 && abs(c1 - c2) == 1) {
                int left = min(c1, c2);
                vehicles.push_back({1, true, 2, 2, left, 6, 7});
            }
        }
    }
    id_pos.erase(1);
    for (auto& pr : id_pos) {
        int id = pr.first;
        auto& pts = pr.second;
        int ls = pts.size();
        if (ls == 2 || ls == 3) {
            set<int> rows, cols;
            for (auto [rr, cc] : pts) {
                rows.insert(rr);
                cols.insert(cc);
            }
            bool hor = (rows.size() == 1 && (int)cols.size() == ls);
            bool ver = (cols.size() == 1 && (int)rows.size() == ls);
            if (hor || ver) {
                int le = ls;
                int fi;
                int po;
                if (hor) {
                    fi = *rows.begin();
                    sort(pts.begin(), pts.end(), [](const pair<int, int>& a, const pair<int, int>& b) {
                        return a.second < b.second;
                    });
                    po = pts[0].second;
                    bool consec = true;
                    for (int k = 1; k < le; ++k) {
                        if (pts[k].second != po + k) {
                            consec = false;
                            break;
                        }
                    }
                    if (consec) {
                        int mp = 5 - le + 1;
                        int np = mp + 1;
                        vehicles.push_back({id, true, le, fi, po, mp, np});
                        continue;
                    }
                } else {
                    fi = *cols.begin();
                    sort(pts.begin(), pts.end(), [](const pair<int, int>& a, const pair<int, int>& b) {
                        return a.first < b.first;
                    });
                    po = pts[0].first;
                    bool consec = true;
                    for (int k = 1; k < le; ++k) {
                        if (pts[k].first != po + k) {
                            consec = false;
                            break;
                        }
                    }
                    if (consec) {
                        int mp = 5 - le + 1;
                        int np = mp + 1;
                        vehicles.push_back({id, false, le, fi, po, mp, np});
                        continue;
                    }
                }
            }
        }
    }
    int n = vehicles.size();
    vector<int> num_p(n);
    for (int i = 0; i < n; ++i) {
        num_p[i] = vehicles[i].num_p;
    }
    long long total = 1;
    for (int np : num_p) {
        total *= np;
        if (total > 20000000LL) total = 20000000LL; // cap for safety
    }
    vector<int> solving_dist(total, -1);
    queue<long long> q;
    vector<int> gpos(n, 0);
    gpos[0] = 6;
    int gboard[6][6] = {};
    generate(1, gpos, gboard, q, solving_dist, vehicles, num_p, total);
    // backwards BFS
    while (!q.empty()) {
        long long st = q.front();
        q.pop();
        int d = solving_dist[st];
        vector<int> pos = decode(st, num_p);
        auto moves = possible_moves(pos, vehicles);
        for (auto [ii, newpp, dirr] : moves) {
            vector<int> np = pos;
            np[ii] = newpp;
            long long nst = get_state(np, num_p);
            if (nst < total && solving_dist[nst] == -1) {
                solving_dist[nst] = d + 1;
                q.push(nst);
            }
        }
    }
    // initial pos
    vector<int> init_pos(n);
    for (int i = 0; i < n; ++i) {
        init_pos[i] = vehicles[i].pos;
    }
    long long init_st = get_state(init_pos, num_p);
    // forward BFS
    vector<int> form_d(total, -1);
    vector<long long> came_from(total, -1);
    vector<pair<int, char>> move_used(total, make_pair(-1, ' '));
    queue<long long> q2;
    form_d[init_st] = 0;
    q2.push(init_st);
    int best_D = solving_dist[init_st];
    long long best_st = init_st;
    while (!q2.empty()) {
        long long st = q2.front();
        q2.pop();
        int fd = form_d[st];
        int sd = solving_dist[st];
        if (sd != -1 && sd > best_D) {
            best_D = sd;
            best_st = st;
        }
        vector<int> pos = decode(st, num_p);
        auto moves = possible_moves(pos, vehicles);
        for (auto [ii, newpp, dirr] : moves) {
            vector<int> np = pos;
            np[ii] = newpp;
            long long nst = get_state(np, num_p);
            if (nst < total && form_d[nst] == -1) {
                form_d[nst] = fd + 1;
                came_from[nst] = st;
                move_used[nst] = {vehicles[ii].id, dirr};
                q2.push(nst);
            }
        }
    }
    // reconstruct
    vector<pair<int, char>> seq;
    long long cur = best_st;
    while (form_d[cur] > 0) {
        seq.push_back(move_used[cur]);
        cur = came_from[cur];
    }
    reverse(seq.begin(), seq.end());
    cout << best_D << " " << seq.size() << endl;
    for (auto [vid, dr] : seq) {
        cout << vid << " " << dr << endl;
    }
    return 0;
}