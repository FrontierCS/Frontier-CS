#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if (!(cin >> t)) return 0;
    for (int tc = 0; tc < t; ++tc) {
        int n, m, start;
        long long base_move_count;
        cin >> n >> m >> start >> base_move_count;
        for (int i = 0; i < m; ++i) {
            int u, v;
            cin >> u >> v;
        }
        long long steps = 0;
        while (true) {
            string tok;
            if (!(cin >> tok)) return 0;
            if (tok == "AC" || tok == "F") {
                break;
            }
            int d = stoi(tok);
            vector<int> deg(d), flag(d);
            for (int i = 0; i < d; ++i) {
                int dd, ff;
                cin >> dd >> ff;
                deg[i] = dd;
                flag[i] = ff;
            }
            int choice = 0;
            vector<int> unvisited;
            for (int i = 0; i < d; ++i) if (flag[i] == 0) unvisited.push_back(i);
            auto select_extreme = [&](const vector<int>& list, bool chooseMax) -> int {
                int best = -1;
                for (int id : list) {
                    if (best == -1) best = id;
                    else {
                        if (chooseMax ? (deg[id] > deg[best]) : (deg[id] < deg[best])) best = id;
                    }
                }
                return best;
            };
            if (!unvisited.empty()) {
                bool chooseMax = (steps % 7 != 0);
                choice = select_extreme(unvisited, chooseMax);
            } else {
                vector<int> all(d);
                iota(all.begin(), all.end(), 0);
                bool chooseMax = (steps % 11 != 0);
                choice = select_extreme(all, chooseMax);
            }
            cout << (choice + 1) << endl << flush;
            steps++;
        }
    }
    return 0;
}