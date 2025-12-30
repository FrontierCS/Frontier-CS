#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    cin >> N >> M;
    vector<int> I(M), J(M);
    for (int k = 0; k < M; k++) cin >> I[k] >> J[k];

    int ci = I[0], cj = J[0];
    vector<pair<char,char>> ans;

    auto push_move = [&](char dir, int times) {
        for (int t = 0; t < times; t++) ans.push_back({'M', dir});
    };

    for (int k = 1; k < M; k++) {
        int ti = I[k], tj = J[k];
        if (ti > ci) push_move('D', ti - ci);
        else if (ti < ci) push_move('U', ci - ti);
        ci = ti;

        if (tj > cj) push_move('R', tj - cj);
        else if (tj < cj) push_move('L', cj - tj);
        cj = tj;
    }

    for (auto [a, d] : ans) {
        cout << a << ' ' << d << '\n';
    }
    return 0;
}