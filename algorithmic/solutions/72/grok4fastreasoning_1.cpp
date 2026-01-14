#include <bits/stdc++.h>
using namespace std;

using ull = unsigned long long;

struct Vehicle {
    int id;
    bool horiz;
    int fixed;
    int len;
    int min_pos;
    int max_pos;
};

vector<int> decode(ull s, int nn) {
    vector<int> res(nn);
    for (int i = nn - 1; i >= 0; i--) {
        res[i] = s % 7;
        s /= 7;
    }
    return res;
}

ull encode(const vector<int>& poss, int nn) {
    ull s = 0;
    for (int p : poss) {
        s = s * 7 + p;
    }
    return s;
}

bool is_occupied(int r, int c, const vector<int>& poss, int ignore_i, const vector<Vehicle>& veh, int n) {
    if (r < 0 || r > 5 || c < 0 || c > 5) return false;
    for (int j = 0; j < n; j++) {
        if (j == ignore_i) continue;
        const auto& v = veh[j];
        int pp = poss[j];
        bool covers = false;
        if (v.horiz) {
            if (v.fixed == r && pp <= c && c <= pp + v.len - 1) covers = true;
        } else {
            if (v.fixed == c && pp <= r && r <= pp + v.len - 1) covers = true;
        }
        if (covers) return true;
    }
    return false;
}

int main() {
    vector<vector<int>> board(6, vector<int>(6));
    for (int i = 0; i < 6; i++) {
        for (int j = 0; j < 6; j++) {
            cin >> board[i][j];
        }
    }

    set<int> ids_set;
    for (int i = 0; i < 6; i++) {
        for (int j = 0; j < 6; j++) {
            if (board[i][j] > 0) ids_set.insert(board[i][j]);
        }
    }
    vector<int> id_list(ids_set.begin(), ids_set.end());
    int n = id_list.size();
    vector<Vehicle> veh(n);
    vector<int> init_pos(n);
    int red_idx = -1;
    for (int ii = 0; ii < n; ii++) {
        int id = id_list[ii];
        vector<pair<int, int>> posi;
        for (int r = 0; r < 6; r++) {
            for (int c = 0; c < 6; c++) {
                if (board[r][c] == id) posi.emplace_back(r, c);
            }
        }
        int sz = posi.size();
        bool same_r = true, same_c = true;
        int rr = posi[0].first, cc = posi[0].second;
        for (auto& pr : posi) {
            if (pr.first != rr) same_r = false;
            if (pr.second != cc) same_c = false;
        }
        Vehicle& v = veh[ii];
        v.id = id;
        v.len = sz;
        int min_posi, max_posi;
        if (same_r) {
            v.horiz = true;
            v.fixed = rr;
            if (id == 1) red_idx = ii;
            min_posi = 10, max_posi = -1;
            for (auto& pr : posi) {
                min_posi = min(min_posi, pr.second);
                max_posi = max(max_posi, pr.second);
            }
            v.min_pos = 0;
            v.max_pos = (id == 1 ? 6 : 6 - sz);
        } else {
            v.horiz = false;
            v.fixed = cc;
            min_posi = 10, max_posi = -1;
            for (auto& pr : posi) {
                min_posi = min(min_posi, pr.first);
                max_posi = max(max_posi, pr.first);
            }
            v.min_pos = 0;
            v.max_pos = 6 - sz;
        }
        init_pos[ii] = min_posi;
    }
    assert(red_idx != -1);

    ull init_s = encode(init_pos, n);

    // First BFS: from initial, find all reachable
    queue<ull> q;
    unordered_set<ull> visited;
    unordered_map<ull, pair<ull, pair<int, char>>> came_from;
    unordered_map<ull, int> dist_from_I;
    vector<ull> all_states;
    unordered_map<ull, int> state_idx;
    vector<ull> goals;

    q.push(init_s);
    visited.insert(init_s);
    all_states.push_back(init_s);
    state_idx[init_s] = 0;
    dist_from_I[init_s] = 0;
    came_from[init_s] = {ULLONG_MAX, {0, ' '}};

    while (!q.empty()) {
        ull cur = q.front();
        q.pop();
        vector<int> poss = decode(cur, n);
        int red_p = poss[red_idx];
        if (red_p >= 6) goals.push_back(cur);

        for (int i = 0; i < n; i++) {
            const auto& v = veh[i];
            int p = poss[i];

            // Left/Up
            char d1 = v.horiz ? 'L' : 'U';
            int newp1 = p - 1;
            bool can1 = (newp1 >= v.min_pos);
            int fr1 = -1, fc1 = -1;
            if (can1) {
                if (v.horiz) {
                    fc1 = newp1;
                    fr1 = v.fixed;
                } else {
                    fr1 = newp1;
                    fc1 = v.fixed;
                }
                if (fr1 < 0 || fc1 < 0) can1 = false;
                else if (is_occupied(fr1, fc1, poss, i, veh, n)) can1 = false;
            }
            if (can1) {
                vector<int> newposs = poss;
                newposs[i] = newp1;
                ull news = encode(newposs, n);
                if (visited.find(news) == visited.end()) {
                    visited.insert(news);
                    all_states.push_back(news);
                    state_idx[news] = all_states.size() - 1;
                    came_from[news] = {cur, {v.id, d1}};
                    dist_from_I[news] = dist_from_I[cur] + 1;
                    q.push(news);
                }
            }

            // Right/Down
            char d2 = v.horiz ? 'R' : 'D';
            int newp2 = p + 1;
            bool can2 = (newp2 <= v.max_pos);
            int fr2 = -1, fc2 = -1;
            if (can2) {
                if (v.horiz) {
                    fc2 = p + v.len;
                    fr2 = v.fixed;
                    if (fc2 > 5) {
                        if (!(i == red_idx && d2 == 'R')) can2 = false;
                    } else {
                        if (is_occupied(fr2, fc2, poss, i, veh, n)) can2 = false;
                    }
                } else {
                    fr2 = p + v.len;
                    fc2 = v.fixed;
                    if (fr2 > 5) can2 = false;
                    else if (is_occupied(fr2, fc2, poss, i, veh, n)) can2 = false;
                }
            }
            if (can2) {
                vector<int> newposs = poss;
                newposs[i] = newp2;
                ull news = encode(newposs, n);
                if (visited.find(news) == visited.end()) {
                    visited.insert(news);
                    all_states.push_back(news);
                    state_idx[news] = all_states.size() - 1;
                    came_from[news] = {cur, {v.id, d2}};
                    dist_from_I[news] = dist_from_I[cur] + 1;
                    q.push(news);
                }
            }
        }
    }

    int M = all_states.size();
    const int INF = 1e9;
    vector<int> dist(M, INF);
    queue<int> q2;
    for (auto g : goals) {
        int id = state_idx[g];
        if (dist[id] == INF) {
            dist[id] = 0;
            q2.push(id);
        }
    }

    while (!q2.empty()) {
        int cid = q2.front();
        q2.pop();
        ull cur_st = all_states[cid];
        vector<int> poss = decode(cur_st, n);
        for (int i = 0; i < n; i++) {
            const auto& v = veh[i];
            int p = poss[i];

            // Left/Up
            char d1 = v.horiz ? 'L' : 'U';
            int newp1 = p - 1;
            bool can1 = (newp1 >= v.min_pos);
            int fr1 = -1, fc1 = -1;
            if (can1) {
                if (v.horiz) {
                    fc1 = newp1;
                    fr1 = v.fixed;
                } else {
                    fr1 = newp1;
                    fc1 = v.fixed;
                }
                if (fr1 < 0 || fc1 < 0) can1 = false;
                else if (is_occupied(fr1, fc1, poss, i, veh, n)) can1 = false;
            }
            if (can1) {
                vector<int> newposs = poss;
                newposs[i] = newp1;
                ull news = encode(newposs, n);
                auto it = state_idx.find(news);
                if (it != state_idx.end()) {
                    int nid = it->second;
                    if (dist[nid] == INF) {
                        dist[nid] = dist[cid] + 1;
                        q2.push(nid);
                    }
                }
            }

            // Right/Down
            char d2 = v.horiz ? 'R' : 'D';
            int newp2 = p + 1;
            bool can2 = (newp2 <= v.max_pos);
            int fr2 = -1, fc2 = -1;
            if (can2) {
                if (v.horiz) {
                    fc2 = p + v.len;
                    fr2 = v.fixed;
                    if (fc2 > 5) {
                        if (!(i == red_idx && d2 == 'R')) can2 = false;
                    } else {
                        if (is_occupied(fr2, fc2, poss, i, veh, n)) can2 = false;
                    }
                } else {
                    fr2 = p + v.len;
                    fc2 = v.fixed;
                    if (fr2 > 5) can2 = false;
                    else if (is_occupied(fr2, fc2, poss, i, veh, n)) can2 = false;
                }
            }
            if (can2) {
                vector<int> newposs = poss;
                newposs[i] = newp2;
                ull news = encode(newposs, n);
                auto it = state_idx.find(news);
                if (it != state_idx.end()) {
                    int nid = it->second;
                    if (dist[nid] == INF) {
                        dist[nid] = dist[cid] + 1;
                        q2.push(nid);
                    }
                }
            }
        }
    }

    int max_d = -1;
    int min_form = INT_MAX;
    ull best_s = init_s;
    for (int j = 0; j < M; j++) {
        ull st = all_states[j];
        int dd = dist[j];
        int form = dist_from_I[st];
        if (dd > max_d || (dd == max_d && form < min_form)) {
            max_d = dd;
            min_form = form;
            best_s = st;
        }
    }

    // Reconstruct path
    vector<pair<int, char>> moves;
    ull current = best_s;
    while (current != init_s) {
        auto& pr = came_from[current];
        ull prev = pr.first;
        int vid = pr.second.first;
        char dr = pr.second.second;
        moves.emplace_back(vid, dr);
        current = prev;
    }
    reverse(moves.begin(), moves.end());

    cout << max_d << " " << min_form << endl;
    for (auto& m : moves) {
        cout << m.first << " " << m.second << endl;
    }

    return 0;
}