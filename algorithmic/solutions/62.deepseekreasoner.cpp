#include <bits/stdc++.h>
using namespace std;

int n, m;
vector<vector<int>> pillars; // 1-indexed: pillars[1..n+1], each vector from bottom to top
vector<pair<int, int>> moves;
int move_count = 0;

void move_ball(int from, int to) {
    // assume from has at least one ball and to has at most m-1 balls
    int ball = pillars[from].back();
    pillars[from].pop_back();
    pillars[to].push_back();
    moves.emplace_back(from, to);
    move_count++;
}

bool is_done() {
    vector<int> color_pillar(n+1, -1); // -1: not assigned, -2: multiple pillars
    for (int i = 1; i <= n+1; i++) {
        if (pillars[i].empty()) continue;
        int col0 = pillars[i][0];
        for (int ball : pillars[i]) {
            if (ball != col0) return false; // mixed colors in one pillar
        }
        // pillar i is monochromatic
        if (color_pillar[col0] == -1) {
            color_pillar[col0] = i;
        } else if (color_pillar[col0] != i) {
            return false; // color appears on more than one pillar
        }
    }
    // every color must appear exactly once (since each color has m balls and m>0)
    for (int c = 1; c <= n; c++) {
        if (color_pillar[c] == -1) return false;
    }
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    cin >> n >> m;
    pillars.resize(n+2);
    for (int i = 1; i <= n; i++) {
        for (int j = 0; j < m; j++) {
            int color;
            cin >> color;
            pillars[i].push_back(color);
        }
    }
    // pillar n+1 is initially empty

    while (!is_done()) {
        bool changed = false;
        for (int i = 1; i <= n; i++) {
            if (pillars[i].empty()) continue;
            // check if pillar i is already finished (monochromatic and full)
            bool same_color = true;
            int col0 = pillars[i][0];
            for (int ball : pillars[i]) if (ball != col0) same_color = false;
            if (same_color && (int)pillars[i].size() == m) continue;

            int col = pillars[i].back();
            if (col != i) {
                // try to move to pillar col
                if ((int)pillars[col].size() < m) {
                    move_ball(i, col);
                    changed = true;
                } else {
                    // need to free space in pillar col
                    int target = -1;
                    for (int j = 1; j <= n+1; j++) {
                        if (j != col && j != i && (int)pillars[j].size() < m) {
                            target = j;
                            break;
                        }
                    }
                    if (target != -1) {
                        move_ball(col, target);
                        move_ball(i, col);
                        changed = true;
                    } else {
                        // no free pillar found, skip for now
                    }
                }
            } else {
                // col == i, but we want to move it out to access below
                // only if there is more than one ball on pillar i
                if ((int)pillars[i].size() > 1) {
                    int target = -1;
                    for (int j = 1; j <= n+1; j++) {
                        if (j != i && (int)pillars[j].size() < m) {
                            target = j;
                            break;
                        }
                    }
                    if (target != -1) {
                        move_ball(i, target);
                        changed = true;
                    }
                }
            }
            if (move_count > 10000000) {
                // should not happen, but break to be safe
                break;
            }
        }
        if (!changed) {
            // no progress, break to avoid infinite loop
            break;
        }
    }

    cout << move_count << "\n";
    for (auto& p : moves) {
        cout << p.first << " " << p.second << "\n";
    }
    return 0;
}