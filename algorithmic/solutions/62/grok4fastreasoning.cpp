#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, m;
    cin >> n >> m;
    vector<vector<int>> pillars(n + 2);
    set<int> colors_set;
    for (int i = 1; i <= n; i++) {
        for (int j = 0; j < m; j++) {
            int col;
            cin >> col;
            pillars[i].push_back(col);
            colors_set.insert(col);
        }
    }
    vector<int> color_list(colors_set.begin(), colors_set.end());
    map<int, int> target_pillar;
    for (int i = 0; i < n; i++) {
        target_pillar[color_list[i]] = i + 1;
    }
    vector<pair<int, int>> moves;
    int aux = n + 1;
    // Move all to aux
    for (int i = 1; i <= n; i++) {
        while (!pillars[i].empty()) {
            int col = pillars[i].back();
            pillars[i].pop_back();
            pillars[aux].push_back(col);
            moves.push_back({i, aux});
        }
    }
    // Move from aux to targets
    while (!pillars[aux].empty()) {
        int col = pillars[aux].back();
        pillars[aux].pop_back();
        int tgt = target_pillar[col];
        pillars[tgt].push_back(col);
        moves.push_back({aux, tgt});
    }
    cout << moves.size() << endl;
    for (auto& mv : moves) {
        cout << mv.first << " " << mv.second << endl;
    }
    return 0;
}