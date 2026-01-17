#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, m;
    cin >> n >> m;
    vector<vector<int>> p(n + 2);
    for (int i = 1; i <= n; ++i) {
        p[i].resize(m);
        for (int j = 0; j < m; ++j) {
            cin >> p[i][j];
        }
    }
    vector<pair<int, int>> moves;
    int aux = n + 1;
    // Phase 1: Move all to aux
    for (int i = 1; i <= n; ++i) {
        while (!p[i].empty()) {
            int ball = p[i].back();
            p[i].pop_back();
            p[aux].push_back(ball);
            moves.emplace_back(i, aux);
        }
    }
    // Phase 2: Distribute to targets
    while (!p[aux].empty()) {
        int ball = p[aux].back();
        p[aux].pop_back();
        int target = ball; // Assume color c goes to pillar c
        p[target].push_back(ball);
        moves.emplace_back(aux, target);
    }
    cout << moves.size() << endl;
    for (auto& mv : moves) {
        cout << mv.first << " " << mv.second << endl;
    }
    return 0;
}