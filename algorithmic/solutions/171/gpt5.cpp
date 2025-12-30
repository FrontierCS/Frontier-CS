#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    if (!(cin >> N >> M)) return 0;
    vector<pair<int,int>> p(M);
    for (int k = 0; k < M; ++k) cin >> p[k].first >> p[k].second;

    vector<pair<char,char>> ans;
    int ci = p[0].first, cj = p[0].second;

    auto move_dir = [&](char d){
        ans.emplace_back('M', d);
        if (d == 'U') ci--;
        else if (d == 'D') ci++;
        else if (d == 'L') cj--;
        else if (d == 'R') cj++;
    };

    for (int k = 1; k < M; ++k) {
        int ti = p[k].first, tj = p[k].second;

        while (ci < ti) move_dir('D');
        while (ci > ti) move_dir('U');
        while (cj < tj) move_dir('R');
        while (cj > tj) move_dir('L');
    }

    // Ensure not exceeding 2*N*M actions
    int limit = 2 * N * M;
    int T = min<int>(ans.size(), limit);
    for (int i = 0; i < T; ++i) {
        cout << ans[i].first << ' ' << ans[i].second << '\n';
    }
    return 0;
}