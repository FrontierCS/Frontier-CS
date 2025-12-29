#include <iostream>
#include <vector>
#include <utility>
using namespace std;

int n, m;
vector<vector<int>> poles;
vector<int> cnt;
vector<bool> fixed_pole;
vector<pair<int, int>> moves;

void move_ball(int from, int to) {
    int col = poles[from].back();
    if (from == col) cnt[col]--;
    if (to == col) cnt[col]++;
    poles[from].pop_back();
    poles[to].push_back();
    moves.push_back({from, to});
}

int find_dest(int exclude1, int exclude2 = -1) {
    for (int j = 1; j <= n+1; ++j) {
        if (j == exclude1 || j == exclude2) continue;
        if (fixed_pole[j] && j <= n) continue; // fixed poles are assumed full
        if ((int)poles[j].size() < m) return j;
    }
    return -1;
}

void process_color(int c) {
    while (cnt[c] < m) {
        // Look for a pole i (not c, not fixed) with top ball color c
        int i = -1;
        for (int idx = 1; idx <= n+1; ++idx) {
            if (idx == c) continue;
            if (fixed_pole[idx] && idx <= n) continue;
            if (!poles[idx].empty() && poles[idx].back() == c) {
                i = idx;
                break;
            }
        }
        if (i != -1) {
            if (poles[c].size() < m) {
                move_ball(i, c);
            } else {
                // pole c is full, need to make space by removing a non-c ball
                // first move away any c balls on top of c
                while (!poles[c].empty() && poles[c].back() == c) {
                    int j = find_dest(c);
                    if (j == -1) return; // should not happen
                    move_ball(c, j);
                }
                if (poles[c].empty()) continue; // safety
                // now top of c is not c, move it out
                int j = find_dest(c);
                if (j == -1) return;
                move_ball(c, j);
                // now pole c has m-1 balls, move the c ball from i to c
                move_ball(i, c);
            }
        } else {
            // no pole has c on top, expose by moving any top ball
            int i = -1;
            for (int idx = 1; idx <= n+1; ++idx) {
                if (idx == c) continue;
                if (fixed_pole[idx] && idx <= n) continue;
                if (!poles[idx].empty()) {
                    i = idx;
                    break;
                }
            }
            if (i == -1) {
                // only pole c might have balls
                if (!poles[c].empty()) i = c;
                else return; // no balls? impossible
            }
            int j = find_dest(i);
            if (j == -1) return; // should not happen
            move_ball(i, j);
        }
    }
    // all c balls are on pole c, mark as fixed
    fixed_pole[c] = true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    cin >> n >> m;
    poles.resize(n+2);
    cnt.assign(n+1, 0);
    fixed_pole.assign(n+1, false);
    for (int i = 1; i <= n; ++i) {
        poles[i].resize(m);
        for (int j = 0; j < m; ++j) {
            cin >> poles[i][j];
        }
        // reverse so that back() is top
        // Actually input gives bottom to top, so we keep as is, but we will use back() as top.
        // So we don't need to reverse.
        // Count balls of color i on pole i
        for (int ball : poles[i]) {
            if (ball == i) cnt[i]++;
        }
    }
    // pole n+1 is initially empty
    
    for (int c = 1; c <= n; ++c) {
        process_color(c);
    }
    
    cout << moves.size() << "\n";
    for (auto& move : moves) {
        cout << move.first << " " << move.second << "\n";
    }
    return 0;
}