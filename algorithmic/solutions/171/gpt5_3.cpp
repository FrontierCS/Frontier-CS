#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    if (!(cin >> N >> M)) return 0;
    vector<pair<int,int>> pts(M);
    for (int k = 0; k < M; ++k) cin >> pts[k].first >> pts[k].second;

    vector<pair<char,char>> ops;

    auto push_op = [&](char a, char d){
        ops.emplace_back(a, d);
    };

    int i = pts[0].first, j = pts[0].second;

    auto slide_to_row = [&](int br){
        if (i == br) return;
        if (br == 0) {
            push_op('S','U');
            i = 0;
        } else {
            push_op('S','D');
            i = N-1;
        }
    };
    auto slide_to_col = [&](int bc){
        if (j == bc) return;
        if (bc == 0) {
            push_op('S','L');
            j = 0;
        } else {
            push_op('S','R');
            j = N-1;
        }
    };
    auto move_vertical_to = [&](int ti){
        if (i == ti) return;
        if (i < ti) {
            for (int s = 0; s < ti - i; ++s) push_op('M','D');
        } else {
            for (int s = 0; s < i - ti; ++s) push_op('M','U');
        }
        i = ti;
    };
    auto move_horizontal_to = [&](int tj){
        if (j == tj) return;
        if (j < tj) {
            for (int s = 0; s < tj - j; ++s) push_op('M','R');
        } else {
            for (int s = 0; s < j - tj; ++s) push_op('M','L');
        }
        j = tj;
    };

    for (int k = 1; k < M; ++k) {
        int ti = pts[k].first, tj = pts[k].second;

        int cost0 = abs(ti - i) + abs(tj - j);

        int br = (ti <= (N-1 - ti)) ? 0 : (N-1);
        int bc = (tj <= (N-1 - tj)) ? 0 : (N-1);

        int svert = (i != br) ? 1 : 0;
        int shori = (j != bc) ? 1 : 0;

        int cost1 = svert + abs(tj - j) + abs(ti - br);
        int cost2 = shori + abs(ti - i) + abs(tj - bc);
        int cost3 = svert + shori + abs(ti - br) + abs(tj - bc);

        int bestType = 0;
        int bestCost = cost0;
        if (cost1 < bestCost) { bestCost = cost1; bestType = 1; }
        if (cost2 < bestCost) { bestCost = cost2; bestType = 2; }
        if (cost3 < bestCost) { bestCost = cost3; bestType = 3; }

        if (bestType == 0) {
            // Moves only: vertical then horizontal
            move_vertical_to(ti);
            move_horizontal_to(tj);
        } else if (bestType == 1) {
            // Slide vertically to boundary near target, then move horizontally, then move vertically to target
            slide_to_row(br);
            move_horizontal_to(tj);
            if (br == 0) {
                move_vertical_to(ti); // moving down from 0 to ti
            } else {
                move_vertical_to(ti); // moving up from N-1 to ti
            }
        } else if (bestType == 2) {
            // Slide horizontally to boundary near target, then move vertically, then move horizontally to target
            slide_to_col(bc);
            move_vertical_to(ti);
            if (bc == 0) {
                move_horizontal_to(tj); // moving right from 0 to tj
            } else {
                move_horizontal_to(tj); // moving left from N-1 to tj
            }
        } else {
            // Slide vertically to boundary near target, slide horizontally to boundary near target,
            // then move vertically and horizontally to target
            slide_to_row(br);
            slide_to_col(bc);
            if (br == 0) {
                move_vertical_to(ti);
            } else {
                move_vertical_to(ti);
            }
            if (bc == 0) {
                move_horizontal_to(tj);
            } else {
                move_horizontal_to(tj);
            }
        }
    }

    for (auto &op : ops) {
        cout << op.first << ' ' << op.second << '\n';
    }
    return 0;
}