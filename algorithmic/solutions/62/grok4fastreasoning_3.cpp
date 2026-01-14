#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, m;
    cin >> n >> m;
    vector<vector<int>> pillars(n + 2);
    for (int i = 1; i <= n; i++) {
        pillars[i].resize(m);
        for (int j = 0; j < m; j++) {
            cin >> pillars[i][j];
        }
    }
    vector<pair<int, int>> seq;
    for (int c = 1; c <= n; c++) {
        int t = c;
        int aux = n + 1;
        // clear t to aux
        while (!pillars[t].empty()) {
            int x = t, y = aux;
            int ball = pillars[x].back();
            pillars[x].pop_back();
            pillars[y].push_back(ball);
            seq.push_back({x, y});
        }
        // to_process
        vector<int> to_process;
        for (int s = c + 1; s <= n; s++) to_process.push_back(s);
        to_process.push_back(aux);
        for (int s : to_process) {
            while (!pillars[s].empty()) {
                int ball = pillars[s].back();
                int x = s;
                int y = (ball == c ? t : ball);
                if (y == x) y = aux;
                pillars[x].pop_back();
                pillars[y].push_back(ball);
                seq.push_back({x, y});
            }
        }
    }
    cout << seq.size() << endl;
    for (auto p : seq) {
        cout << p.first << " " << p.second << endl;
    }
    return 0;
}