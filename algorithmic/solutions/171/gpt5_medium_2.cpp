#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    if (!(cin >> N >> M)) return 0;
    vector<pair<int,int>> pts(M);
    for (int i = 0; i < M; i++) cin >> pts[i].first >> pts[i].second;

    int ci = pts[0].first, cj = pts[0].second;
    vector<pair<char,char>> actions;
    auto moveDir = [&](char d) {
        actions.emplace_back('M', d);
        if (d == 'U') ci--;
        else if (d == 'D') ci++;
        else if (d == 'L') cj--;
        else if (d == 'R') cj++;
    };

    for (int k = 1; k < M; k++) {
        int ti = pts[k].first, tj = pts[k].second;
        while (ci < ti) moveDir('D');
        while (ci > ti) moveDir('U');
        while (cj < tj) moveDir('R');
        while (cj > tj) moveDir('L');
    }

    for (auto &p : actions) {
        cout << p.first << " " << p.second << "\n";
    }
    return 0;
}