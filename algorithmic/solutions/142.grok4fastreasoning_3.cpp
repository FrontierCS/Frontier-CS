#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    cin >> n >> m;
    
    vector<vector<int>> poles(n + 2);
    vector<vector<int>> cnt(n + 1, vector<int>(n + 2, 0));
    for (int i = 1; i <= n; ++i) {
        poles[i].resize(m);
        for (int j = 0; j < m; ++j) {
            cin >> poles[i][j];
            ++cnt[poles[i][j]][i];
        }
    }
    
    vector<tuple<int, int, int>> cands;
    for (int c = 1; c <= n; ++c) {
        for (int p = 1; p <= n; ++p) {
            cands.emplace_back(cnt[c][p], c, p);
        }
    }
    sort(cands.rbegin(), cands.rend());
    
    vector<int> target(n + 1, 0);
    vector<bool> used(n + 2, false);
    for (auto& t : cands) {
        int val, c, p;
        tie(val, c, p) = t;
        if (target[c] == 0 && !used[p]) {
            target[c] = p;
            used[p] = true;
        }
    }
    
    int temp = n + 1;
    for (int p = 1; p <= n + 1; ++p) {
        if (!used[p]) {
            temp = p;
            break;
        }
    }
    
    vector<int> color_of(n + 2, 0);
    for (int c = 1; c <= n; ++c) {
        color_of[target[c]] = c;
    }
    
    vector<pair<int, int>> moves;
    int iter = 0;
    const int MAX_ITER = 2000000;
    bool changed;
    do {
        changed = false;
        ++iter;
        if (iter > MAX_ITER) break;
        
        // Permanent moves
        bool did_move = false;
        for (int x = 1; x <= n + 1 && !did_move; ++x) {
            if (poles[x].empty()) continue;
            int col = poles[x].back();
            int y = target[col];
            if (y == 0 || y == x) continue;
            if ((int)poles[y].size() >= m) continue;
            bool can_place = poles[y].empty() || poles[y].back() == col;
            if (can_place) {
                moves.emplace_back(x, y);
                int ball = poles[x].back();
                poles[x].pop_back();
                poles[y].push_back(ball);
                changed = true;
                did_move = true;
            }
        }
        if (changed) continue;
        
        // Enabling moves
        did_move = false;
        for (int x = 1; x <= n + 1 && !did_move; ++x) {
            if ((int)poles[x].size() < 2) continue;
            int col_top = poles[x].back();
            auto it = poles[x].rbegin();
            ++it;
            int col_sec = *it;
            int y = target[col_sec];
            if (y == 0 || y == x) continue;
            if ((int)poles[y].size() >= m) continue;
            bool can_place = poles[y].empty() || poles[y].back() == col_sec;
            if (can_place && x != temp && (int)poles[temp].size() < m) {
                moves.emplace_back(x, temp);
                int ball = poles[x].back();
                poles[x].pop_back();
                poles[temp].push_back(ball);
                changed = true;
                did_move = true;
            }
        }
        if (changed) continue;
        
        // Default to temp
        if ((int)poles[temp].size() < m) {
            int chosen_x = -1;
            int max_h = -1;
            for (int x = 1; x <= n + 1; ++x) {
                if (x == temp || poles[x].empty()) continue;
                int col = poles[x].back();
                bool is_complete_like = ((int)poles[x].size() == m && color_of[x] != 0 && col == color_of[x]);
                if (is_complete_like) continue;
                if ((int)poles[x].size() > max_h || ((int)poles[x].size() == max_h && x < chosen_x)) {
                    max_h = poles[x].size();
                    chosen_x = x;
                }
            }
            if (chosen_x != -1) {
                moves.emplace_back(chosen_x, temp);
                int ball = poles[chosen_x].back();
                poles[chosen_x].pop_back();
                poles[temp].push_back(ball);
                changed = true;
            }
        }
        if (changed) continue;
        
        // Evacuate from temp
        if (!poles[temp].empty() && (int)poles[temp].size() == m) {
            int chosen_y = -1;
            int min_s = m + 1;
            for (int y = 1; y <= n + 1; ++y) {
                if (y == temp || (int)poles[y].size() >= m) continue;
                int s = poles[y].size();
                if (s < min_s || (s == min_s && y < chosen_y)) {
                    min_s = s;
                    chosen_y = y;
                }
            }
            if (chosen_y != -1) {
                moves.emplace_back(temp, chosen_y);
                int ball = poles[temp].back();
                poles[temp].pop_back();
                poles[chosen_y].push_back(ball);
                changed = true;
            }
        }
    } while (changed && iter < MAX_ITER);
    
    cout << moves.size() << '\n';
    for (auto& mv : moves) {
        cout << mv.first << " " << mv.second << '\n';
    }
    
    return 0;
}