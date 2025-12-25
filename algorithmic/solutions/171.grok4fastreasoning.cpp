#include <bits/stdc++.h>
using namespace std;

int main() {
    int N, M;
    cin >> N >> M;
    vector<pair<int, int>> pos(M);
    for (int k = 0; k < M; k++) {
        cin >> pos[k].first >> pos[k].second;
    }
    pair<int, int> cur = pos[0];
    vector<string> actions;
    for (int t = 1; t < M; t++) {
        int dx = pos[t].first - cur.first;
        int dy = pos[t].second - cur.second;
        // Handle rows first
        if (dx != 0) {
            char rowdir = (dx > 0) ? 'D' : 'U';
            int rowsteps = abs(dx);
            for (int k = 0; k < rowsteps; k++) {
                actions.push_back("M " + string(1, rowdir));
            }
        }
        // Then columns
        if (dy != 0) {
            char coldir = (dy > 0) ? 'R' : 'L';
            int colsteps = abs(dy);
            for (int k = 0; k < colsteps; k++) {
                actions.push_back("M " + string(1, coldir));
            }
        }
        cur = pos[t];
    }
    for (auto& s : actions) {
        cout << s << endl;
    }
    return 0;
}